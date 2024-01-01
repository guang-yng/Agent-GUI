import json
import time
from web import WebEnv
from request_openai import call_openai_gpt4v

GPT4V_API_QA_prompt = """## candidate actions
type Click = { action: "click", element: number }
type Typing = { action: "typing", text: string}
type Scroll = { action: "scroll", x: float, y: float }
type InfoLog = { action: "information", text: string }
type Done = { action: "done" }

## action explains
- Click action performs a click on a specified element by its index.
- Typing action types the given text into the current field in focus. Optionally, a specific key (like 'Enter') can be pressed afterwards.
- Scroll action scrolls the web page. 'x' and 'y' represent the relative position (percentage) of the width and height of the page to scroll to.
- InfoLog action is used for logging information, such as important strings or observations relevant to the task.
- Done action signifies the completion of the task.

## response format
{
    briefExplanation: string,
    nextAction: Click | Input | Enter | Scroll | InfoLog | Done
}

## task
TASK_INS

## history
HISTORY_LIST

## previously browsed information
INFORMATION

## instructions
The given image is a screenshot of current browser page with elements labled. 
Think step by step and look carefully into the elements and THEIR LABELS.
Generate the next action and navigate the browser to achieve the task mentioned above.
Output your response in a json markdown code block.

## examples
{
    "briefExplanation": "Clicking on the search button to initiate the search. Because the search button is labled with 5 in the screenshot, we click the 5-th element in the page.",
    "nextAction": {
        "action": "click",
        "element": 5
    }
}
{
    "briefExplanation": "Look through the commodities listed in the website. The prices are $314.99, $17.99 and $9.99 respectively. Log this information for future comparison.",
    "nextAction": {
        "action": "information",
        "text": "Price lists: \\n1. Carrera Smart Glasses with Alexa | Smart audi... $314.99\\n2. Polarized Sunglasses for Men and Women Semi... $17.99\n3. Sunglasses Men Polarized Sunglasses for Mens an... $9.99\n"
    }
}
{
    "briefExplanation": "The prices recorded are $3.4, $5.3 and $3.30 respectively. To check whether cheaper commodities exists, scroll down for the full list.",
    "nextAction": {
        "action": "scroll",
        "x": 0.0,
        "y": 10.0,
    }
}
{
    "briefExplanation": "To get more information about the product, the correct way is to click the 'more information' botton. However, it is not labeled with any number. Try scroll down.",
    "nextAction": {
        "action": "scroll",
        "x": 0.0,
        "y": 10.0,
    }
}
{
    "briefExplanation": "Clicking on the search botton. Because the pop-up window covers the botton, the search botton is not labeld. We can try enter instead.",
    "nextAction": {
        "action": "typing",
        "text": "\\n",
    }
}
"""
#type Enter = { action: "enter", element: number }


def build_prompt(instruction, history, logs):
    prompt = GPT4V_API_QA_prompt.replace("TASK_INS", instruction)

    if history is None:
        prompt = prompt.replace("HISTORY_LIST", "none")
    else:
        history_list = "\n".join(history)
        prompt = prompt.replace("HISTORY_LIST", history_list)

    if logs is None:
        prompt = prompt.replace("INFORMATION", "none")
    else:
        logs_list = "\n".join(logs)
        prompt = prompt.replace("INFORMATION", logs_list)

    return prompt

def run_one_task(instruction, url):
    web_env = WebEnv(debug = True)  # Initialize your WebEnv instance
    action = None
    history = []
    logs = []

    step = 0

    while True:
        # Start the task or perform an action
        if not action:
            data = web_env.goto(url)  # Navigate to the URL
            print("1. Navigated to URL successfully...")
        elif action["action"] == "click":
            element_index = action["element"]
            data = web_env.click(element_index=element_index)
        elif action["action"] == "typing":
            text = action.get("text", "")
            press = action.get("press", None)
            data = web_env.typing(text=text, press=press)
        elif action["action"] == "scroll":
            x = action.get("x", 0.0)
            y = action.get("y", 0.6)
            data = web_env.scroll(x=x, y=y)
        elif action["action"] == "information":
            # Log the information, no actual action on the web page
            log = action.get("text", "")
            print(f"InfoLog: {log}")
            logs.append(log)
        elif action["action"] == "done":
            print("Task completed.")
            # Handle task completion if necessary
            data = None  # No further data since task is completed
            break
        else:
            raise ValueError(f"Invalid action: {action}")
        
        print("please waiting 3 seconds...")
        time.sleep(3)
        base64_capture_bbox, elements = data["data"][0]["data"], data["data"][1]["data"]

        # Build the prompt
        prompt = build_prompt(instruction, history, logs)

        # Call GPT-4V
        gpt4v_res = call_openai_gpt4v(prompt, base64_capture_bbox)
        print(gpt4v_res)
        # Process the action
        str_action  = gpt4v_res.split("```json")[-1].split("```")[0]
        action = json.loads(str_action)["nextAction"]

        # Update history and logs
        history.append(str_action)

    return logs

if __name__ == "__main__":
    instruction = "Find a one-way flight ticket from Seattle to San Francisco on Mar 8 with Delta airline. Tell me the price and flight information."
    url = "https://www.google.com/"
    run_one_task(instruction, url)