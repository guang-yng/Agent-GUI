from openai import OpenAI
import requests

def call_openai_gpt4v(prompt, base64_capture_bbox):
    client = OpenAI(
        api_key="p23zbhgxnd7c49uukhya8vcrxeyd74x6",
        base_url="https://openapi.laiye.com/open/api/v1/"
    )

    json_content = [
        {
            "type": "text",
            "text": prompt,
        },
        # {
        #     "type": "image_url",
        #     "image_url":{
        #         "url": f"data:image/jpeg;base64,{base64_capture}"
        #     }
        # },
        {
            "type": "image_url",
            "image_url":{
                "url": f"data:image/jpeg;base64,{base64_capture_bbox}"
            }
        }
    ]

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": json_content,
            }
        ],
        model="gpt-4-vision-preview",
        max_tokens=1000,
        temperature=0.8,
    )
    res = ""
    try:
        res = chat_completion.choices[0].message.content
    except:
        print(chat_completion)
    return res

if __name__ == "__main__":
    pass