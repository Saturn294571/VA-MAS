"""Optional historical vector-store search; not used by the current TD retriever."""
import os
import json
from langchain.docstore.document import Document
from model.google_model import GoogleEmbeddingModel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.vectorstores.chroma import Chroma
from langchain.retrievers import ParentDocumentRetriever
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains.query_constructor.base import AttributeInfo
from langchain.storage import InMemoryStore

def dict2document(dict: dict, db_name: str):
    """
    Convert a dict to a document in Chroma
    return a document
    """
    if db_name == "blueprint":
        page_content = "The building " + dict["description"] + " contains: \n"
        for block in dict["blocks"]:
            page_content += f"{block['name']} at {block['position']} facing {block['facing']}\n"

        return Document(
            page_content=page_content,
            metadata={"tag": dict["description"]},
            title=dict["description"],
        )

    elif db_name == "conversation":
        return Document(
            page_content=dict["content"],
            metadata={"tag": ""},
            title="",
        )

    elif db_name == "requirement":
        return Document(
            page_content=dict["content"],
            metadata={"tag": ""},
            title="",
        )

    else:
        raise NotImplementedError


def load_db_name(db_name, update=False, verbose=False, json_path="", query_type="ParentDocument"):
    if query_type == "ParentDocument":
        if verbose:
            print(f"Loading {db_name}...")
        json_data = json.load(open(json_path, "r"))
        documents = []
        for item in json_data:
            document = dict2document(item, db_name)
            documents.append(document)
        return documents

    else:
        if os.path.exists(f"db_{db_name}/") and not update:
            vectordb = Chroma(persist_directory=f"db_{db_name}/",
                              embedding_function=GoogleEmbeddingModel())
        else:
            if verbose:
                print(f"Loading {db_name}...")
            json_data = json.load(open(json_path, "r"))
            documents = []
            for item in json_data:
                document = dict2document(item, db_name)
                documents.append(document)
            # Split
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=500)
            splits = text_splitter.split_documents(documents)

            # VectorDB
            embedding = GoogleEmbeddingModel()
            vectordb = Chroma.from_documents(documents=splits, embedding=embedding,
                                             persist_directory=f"db_{db_name}/")
    return vectordb


def query_from_db(llm, db_dict, db_name, query="", verbose=False, query_type=""):
    if db_name not in db_dict.keys():
        db_dict[db_name + f"_{query_type}"] = load_db_name(db_name=db_name, update=False, verbose=verbose,
                                                           json_path=f"experience/{db_name}.json",
                                                           query_type=query_type)
    vectordb = db_dict[db_name + f"_{query_type}"]
    if query_type == "SelfQuery":
        metadata_field_info = [
            AttributeInfo(
                name="tag",
                description="the description",
                type="string",
            ),
        ]
        self_query_retriever = SelfQueryRetriever.from_llm(
            llm,
            vectordb,
            f"{db_name}_database",
            metadata_field_info,
        )
        unique_docs = self_query_retriever.invoke(query)
    elif query_type == "ParentDocument":
        # This text splitter is used to create the child documents
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=400)
        # The vectorstore to use to index the child chunks
        vectorstore = Chroma(
            collection_name="full_documents", embedding_function=GoogleEmbeddingModel()
        )
        # The storage layer for the parent documents
        store = InMemoryStore()
        retriever = ParentDocumentRetriever(
            vectorstore=vectorstore,
            docstore=store,
            child_splitter=child_splitter,
        )
        retriever.add_documents(vectordb, ids=None)
        unique_docs = retriever.get_relevant_documents(query, top_k=1)

    else:
        # MultiQuery
        retriever_from_llm = MultiQueryRetriever.from_llm(
            retriever=vectordb.as_retriever(), llm=llm
        )
        unique_docs = retriever_from_llm.get_relevant_documents(query=query, top_k=1)

    text_results = ""
    for doc in unique_docs:
        text_results += doc.page_content + "\n"
    if verbose:
        print(f"[Debug] {text_results[:10]} ... {text_results[-10:]}\n")

    return f"{text_results}", unique_docs
