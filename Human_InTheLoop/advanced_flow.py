from langgraph.graph import StateGraph ,START , END 
from typing import TypedDict,Annotated
from langchain_core.messages import AIMessage ,HumanMessage,BaseMessage,ToolMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langgraph.types import interrupt,Command
from langchain.tools import tool,tool_node
from langgraph.prebuilt import ToolNode,tools_condition
import httpx
import os 

load_dotenv()

alpha_vantage_key = os.getenv("ALPHAVANTAGE_API_KEY")
weather_key = os.getenv("OPENWEATHER_API_KEY")

model = ChatGroq( model="openai/gpt-oss-20b",
    temperature=0.7)

class graph_state(TypedDict):

    messages:Annotated[list[BaseMessage] , add_messages]




@tool   
def stock_market_tool(symbol:str)->dict:

    ''' This is a stock market tool , provides the latest stock value of any stock .'''
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={alpha_vantage_key}"
    with httpx.Client(timeout=10.0) as asyncclient:
        try:
            r =  asyncclient.get(url)
            data = r.json()

            return data
        except Exception as e:
            return {
                "error":str(e)
            }

@tool 
def buy_stock(state:graph_state,stock_name:str,stock_quantity:int,stock_price:float):
    if stock_quantity>0:
        '''A dummy tool to imitate as used for buying a stock '''
        decision = interrupt(
            {"value":"approval",
                    "reason":"stock will be bought according to users choice.",
                    "question":state['messages'][-1].content if state['messages'] else [],
                    "instruction":f"are you willing to buy {stock_quantity} stocks of {stock_name} costing you {stock_quantity*stock_price} ?"
                }
        )

        if decision['response']=="no" or decision['response']=="No":
                return {"messages":(ToolMessage(content="This stock will not be bought."))}
        elif decision['response']=="yes" or decision['response']=="Yes":
                return {"messages":(ToolMessage(content=f"The  {stock_quantity} stocks of {stock_name} bought for {stock_quantity*stock_price}."))}
        else:
             return {"messages":(ToolMessage(content="Please answer with yes or no ."))}
    else:
         return "the stock quantity is not valid ."

tools = [stock_market_tool,buy_stock]

llm_with_tool = model.bind_tools(tools)
tool_node = ToolNode(tools)

def chat_node(state:graph_state):

     res = llm_with_tool.invoke(state['messages'])

     return {'messages':[res]}

graph = StateGraph(graph_state)

graph.add_node("chat_node",chat_node)
graph.add_node("tools",tool_node)

graph.add_edge(START,"chat_node")
graph.add_conditional_edges("chat_node",tools_condition)
graph.add_edge("tools","chat_node")
checkpointer = InMemorySaver()
compiler = graph.compile(checkpointer=checkpointer)

if __name__ == "__main__":

    while True:
            config = {"configurable":{
                "thread_id":1
            }}

            user_query = input("You:")

            if user_query in ['exit',"Exit"]:
                 break

            check1 = compiler.invoke({"messages":[HumanMessage(content=user_query)]},  config=config)

            interruppt = check1.get("__interrupt__",[])

            if interruppt:
                intr_res = interruppt[0].value['instruction']
                print(f"{intr_res}")
                user_res = input("Your decision:")
                check2 = compiler.invoke(Command(resume={"response":user_res}),config=config)
                print(f"Chatbot:{check2['messages'][-1].content}")
            else:
                 print(f"Chatbot:{check1['messages'][-1].content}")

            
        

            




