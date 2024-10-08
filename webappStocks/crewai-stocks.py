import json
import os
from datetime import datetime

import yfinance as yf

from crewai import Agent, Task, Crew, Process

from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchResults

import streamlit as st

# Aqui usando um dos métodos da biblioteca onde passamos o código da Ação, a data início e a data fim E fazemos download desses dados
# Criando a Tool que será utilizada pelo Agente de pesquisa de preços de ações
def fetch_preco_stock(ticket):
    stock = yf.download(ticket, start="2023-08-08", end="2024-08-08")
    return stock 

yahoo_finance_tool = Tool(
     name = "Yahoo Finance Tool",
     description = "Fetches stocks prices for {ticket} from the last year about a specific company from Yahoo Finance API",
     func = lambda ticket: fetch_preco_stock(ticket)
)

# IMPORTANDO OPENAI LLM - GPT
os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']
llm = ChatOpenAI(model = "gpt-3.5-turbo")

# Agente responsável por pesquisar os preços da ação descrita pelo usuário
stockPriceAnalyst = Agent(
    role = "Senior Stock Price Analyst",
    goal = "Find the {ticket} stocks price and analyses trends",
    backstory = """ You're a highly experienced in analyzing the price of an specific stock
    and make predictions about its future price.""",
    verbose = True,
    llm = llm,
    max_iter = 5, # Ou seja pode ficar no ciclo de Perception, Reason Action até 5 vezes
    memory = True,
    tools = [yahoo_finance_tool],
    allow_delegation = False
)

# Tarefa respectiva dele.
getStockPrice = Task(
    description = "Analyze the stock {ticket} price history and create a trend analyses of up, down or sideways",
    expected_output = """ Specify the current trend stock price - up, down or sideways.
    eg. stock = 'APPL, price UP'
    """,
    agent = stockPriceAnalyst
)


# IMPORTAR TOOL DE PESQUISA
# Utilizando a API de pesquisa do DuckDuckGo como uma tool de pesquisa para o agente de notícias
search_tool = DuckDuckGoSearchResults(backend = 'news', num_results = 10)


# Agente responsável por analisar notícias sobre a empresa que possui a ação
newsAnalyst = Agent(
    role = "Stock News Analyst",
    goal = """Create a short summary of the market news related to the stock {ticket} company. Specify the current 
    trend - up, down or sideways with the news context. For each request stock asset, specify a number 
    between 0 and 100, where 0 is extreme fear and 100 is extreme greed.""",
    backstory = """ You're a highly experienced in analyzing the market trends and news and have tracked assets for
    more than 10 years. 

    You're also master level analyst in the tradicional markets and have deep understanding of human psychology.

    You understand news, theirs titles and information, but you look at those with a health dose of skepticism.
    You consider also the source of the news articles.
""",
    verbose = True,
    llm = llm,
    max_iter = 10,
    memory = True,
    tools = [search_tool],
    allow_delegation = False
)

# Tarefa do agente de notícias
get_news = Task (
    description = f"""Take the stock and always include BTC to it (if not request). 
    Use the search tool to search each one individually.
    
    The current date is {datetime.now()}.
    
    Compose the results into a helpfull report""",
    expected_output = """A summary of the overall market and one sentence summary for each request asset.
    Include a fear/greed score for each asset based on the news. Use format:
    <STOCK ASSET>
    <SUMMARY BASED ON NEWS>
    <TREND PREDICTION>
    <FEAR/GREED SCORE>
    """,
    agent = newsAnalyst
)

# Agente responsável por analisar o que os outros dois fizeram e escrever sobre elas de uma forma estruturada
stockAnalystWrite = Agent(
    role = "Senior Stock Analyst Writer",
    goal = """Analyze the trends price and news and write an insightful compelling and informative 3 paragraph long newsletter based on the stock report
    and price trend.""",
    backstory = """You're widely accepted as the best stock analyst in the market. You understand complex concepts
    and create compelling stories and narratives that resonate with wider audiences.

    You understand macro factors and combine multiple theories - eg. cycle theory and fundamental analyses.
    You're able to hold multiple opinions when analyzing anything.
""",
    verbose = True,
    llm = llm,
    max_iter = 5,
    memory = True,
    allow_delegation = True
)

# Tarefa do Agente Escritor
writeAnalyses = Task (
    description = """Use the stock price trend and the stock news report to create and analyses and write the
    newsletter about the {ticket} company that is brief and highlights the most important points.
    Focus on the stock price trend, news and fear/greed score. What are the near future considerations?
    Include the previous analyses of stock trend and news summary.
    """,
    expected_output = """An eloquent 3 paragraphs newsletter formatted as markdown in an easy readable manner.
    It should contain:
    - 3 bullets executive summary
    - Introduction - set the overall picture and spike up the interest
    - main part provides the meat of the analysis including the news summary and fear/greed scores
    - summary - key facts and concrete future trend prediction - up, down or sideways.
    """,
    agent = stockAnalystWrite,
    context = [getStockPrice, get_news]
)


# Utilizado o Hierárquico, pois no fim do dia o Agente Que escreve será o Administrador dos outros agentes
    # Configurando nossa tripulação de agentes para trabalharem
crew = Crew(
    agents = [stockPriceAnalyst, newsAnalyst, stockAnalystWrite],
    tasks = [getStockPrice, get_news, writeAnalyses],
    verbose = 2,
    process= Process.hierarchical,
    full_output=True,
    share_crew=False,
    manager_llm=llm,
    max_iter=15
)

# Execução de um módulo Web bem simples, usando Streamlit
with st.sidebar:
    st.header('Digite a Ação que quer Pesquisar')

    with st.form(key='research_form'):
        topic = st.text_input("Selecione o Ticket")
        submit_button = st.form_submit_button(label = "Pesquisar")

if submit_button:
    if not topic:
        st.error("Por favor preencha o campo de pesquisa do ticket")
    else:
        results = crew.kickoff(inputs = { 'ticket': topic })

        st.subheader("Resultados da sua pesquisa:")
        st.write(results['final_output'])