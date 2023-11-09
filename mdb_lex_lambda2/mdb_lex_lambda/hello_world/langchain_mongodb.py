from langchain.chains import RetrievalQA
from mongodb_retriever import MDBContextRetriever
from langchain.prompts import PromptTemplate
from langchain.llms import SagemakerEndpoint
from langchain.llms.sagemaker_endpoint import LLMContentHandler
import json
import os

def build_chain():

    mongodb_uri = os.environ["ATLAS_URI"]
    endpoint_name = os.environ["LLM_ENDPOINT"]
    aws_region = os.environ["AWS_REGION1"]

    print("AWS Region: " + str(aws_region))

    class ContentHandler(LLMContentHandler):
        content_type = "application/json"
        accepts = "application/json"

        def transform_input(self, prompt: str, model_kwargs: dict) -> bytes:
            input_str = json.dumps({"text_inputs": prompt, **model_kwargs})
            return input_str.encode('utf-8')

        def transform_output(self, output: bytes) -> str:
            response_json = json.loads(output.read().decode("utf-8"))
            return response_json["generated_texts"][0]

    content_handler = ContentHandler()

    llm=SagemakerEndpoint(
            endpoint_name=endpoint_name,
            region_name=aws_region,
            model_kwargs={"temperature":1e-10, "max_length": 500},
            content_handler=content_handler
        )

    retriever = MDBContextRetriever(mongodb_uri= mongodb_uri, k=3,
                                    return_source_documents=False
                                    )

    prompt_template = """
    The following is a friendly conversation between a human and an AI.
    The AI is talkative and provides lots of specific details from its context.
    If the AI does not know the answer to a question, it truthfully says it
    does not know.
    {context}
    Instruction: Based on the above documents, summarize the following statement, {question} Answer "don't know" if not present in the document. Solution:
    """
    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    chain_type_kwargs = {"prompt": PROMPT}
    qa = RetrievalQA.from_chain_type(
        llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs=chain_type_kwargs,
        return_source_documents=True
    )
    return qa

def run_chain(chain, prompt: str, history=[]):
    result = chain(prompt)
    # To make it compatible with chat samples
    return {
        "answer": result['result'],
        "source_documents": result['source_documents']
    }

if __name__ == "__main__":

    input_text = "describe fish that lives in the ocean"
    chain = build_chain()
    result = run_chain(chain, input_text)

    print("Input text is:",input_text)
    print("LLM generated text is:",result['answer'])

