import os

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from dotenv import load_dotenv

from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma

import bs4

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

load_dotenv()


openai_api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openai_api_key)


def researchAgent(query, llm):
  tools = load_tools(["ddg-search", "wikipedia"], llm=llm)
  prompt = hub.pull("hwchase17/react")
  agent = create_react_agent(llm, tools, prompt)
  agent_executor = AgentExecutor(agent=agent, tools=tools, prompt=prompt, verbose=True)
  webContext = agent_executor.invoke({ "input": query })
  return webContext['output']

# print(researchAgent(query, llm))

def loadData():
  loader = WebBaseLoader(
  web_paths= ("https://www.dicasdeviagem.com/pousadas-no-interior-do-parana/",),
  bs_kwargs=dict(parse_only=bs4.SoupStrainer(class_=("postcontentwrap", "pagetitleloading background-imaged loading-dark"))),)
  docs = loader.load()
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
  splits = text_splitter.split_documents(docs)
  vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())
  retriever = vectorstore.as_retriever()
  return retriever

def getRelevantDocs(query):
  retriever = loadData()
  relevant_documents = retriever.invoke(query)
  print(relevant_documents)
  return relevant_documents

def supervisorAgent(query, llm, webContext, relevant_documents):
  
  prompt_template = """
  Você é um gerente de uma agência de viagens. Sua resposta final deverá ser um roteiro de viagem completo e detalhado. 
  Utilize o contexto de eventos e preços de passagens, o input do usuário e também os documentos relevantes para elaborar o roteiro.
  Contexto: {webContext}
  Documento relevante: {relevant_documents}
  Usuário: {query}
  Assistente:
  """

  prompt = PromptTemplate(
    input_variables=['webContext', 'relevant_documents', 'query'],
    template = prompt_template
  )

  sequence = RunnableSequence(prompt | llm)
  response = sequence.invoke({"webContext": webContext, "relevant_documents": relevant_documents, "query": query})
  return response

def getResponse(fromLocation, toLocation, llm):
  
  query= f"""
  Vou viajar para {toLocation} em entre os dias  19/07/2024 e 21/07/2024.
  Quero que faça para um roteiro de viagem para mim com eventos que irão ocorrer na data da viagem e com o preço de passagem de {fromLocation} para {toLocation}.
  """
  
  webContext = researchAgent(query, llm)
  relevant_documents = getRelevantDocs(query)
  response = supervisorAgent(query, llm, webContext, relevant_documents)
  return response

print(getResponse('Porto Ferreira - SP', "Londrina - PR", llm).content)