# 流式输出
流式输出
Documentation Index
Fetch the complete documentation index at: https://docs.siliconflow.cn/llms.txt

Use this file to discover all available pages before exploring further.

​
1. 在 python 中使用流式输出
​
1.1 基于 OpenAI 库的流式输出
在一般场景中，推荐您使用 OpenAI 的库进行流式输出。
from openai import OpenAI

client = OpenAI(
    base_url='https://api.siliconflow.cn/v1',
    api_key='your-api-key'
)

# 发送带有流式输出的请求
response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V2.5",
    messages=[
        {"role": "user", "content": "SiliconFlow公测上线，每用户送3亿token 解锁开源大模型创新能力。对于整个大模型应用领域带来哪些改变？"}
    ],
    stream=True  # 启用流式输出
)

# 逐步接收并处理响应
for chunk in response:
    if not chunk.choices:
        continue
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
    if chunk.choices[0].delta.reasoning_content:
        print(chunk.choices[0].delta.reasoning_content, end="", flush=True)
​
1.2 基于 requests 库的流式输出
如果您有非 openai 的场景，如您需要基于 request 库使用 SiliconFlow API，请您注意： 除了 payload 中的 stream 需要设置外，request 请求的参数也需要设置stream = True, 才能正常按照 stream 模式进行返回。
from openai import OpenAI
import requests
import json
   
url = "https://api.siliconflow.cn/v1/chat/completions"
   
payload = {
        "model": "deepseek-ai/DeepSeek-V2.5", # 替换成你的模型
        "messages": [
            {
                "role": "user",
                "content": "SiliconFlow公测上线，每用户送3亿token 解锁开源大模型创新能力。对于整个大模型应用领域带来哪些改变？"
            }
        ],
        "stream": True # 此处需要设置为stream模式
}

headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": "Bearer your-api-key"
    }
   
response = requests.post(url, json=payload, headers=headers, stream=True) # 此处request需要指定stream模式


# 打印流式返回信息
if response.status_code == 200:
    full_content = ""
    full_reasoning_content = ""

    for chunk in response.iter_lines():
        if chunk:
            chunk_str = chunk.decode('utf-8').replace('data: ', '')
            if chunk_str != "[DONE]":
                chunk_data = json.loads(chunk_str)
                delta = chunk_data['choices'][0].get('delta', {})
                content = delta.get('content', '')
                reasoning_content = delta.get('reasoning_content', '')
                if content:
                    print(content, end="", flush=True)
                    full_content += content
                if reasoning_content:
                    print(reasoning_content, end="", flush=True)
                    full_reasoning_content += reasoning_content
else:
    print(f"请求失败，状态码：{response.status_code}")

​
2. curl 中使用流式输出
curl 命令的处理机制默认情况下，curl 会缓冲输出流，所以即使服务器分块（chunk）发送数据，也需要等缓冲区填满或连接关闭后才看到内容。传入 -N（或 --no-buffer）选项，可以禁止此缓冲，让数据块立即打印到终端，从而实现流式输出。
curl -N -s \
  --request POST \
  --url https://api.siliconflow.cn/v1/chat/completions \
  --header 'Authorization: Bearer token' \
  --header 'Content-Type: application/json' \
  --data '{
    "model": "Qwen/Qwen2.5-72B-Instruct",
    "messages": [
      {"role":"user","content":"有诺贝尔数学奖吗？"}
    ],
    "stream": true
}'

# 创建对话
创建对话请求（OpenAI）
Creates a model response for the given chat conversation.

POST
/
chat
/
completions
Documentation Index
Fetch the complete documentation index at: https://docs.siliconflow.cn/llms.txt

Use this file to discover all available pages before exploring further.

Authorizations
​
Authorization
stringheaderrequired
Use the following format for authentication: Bearer

Body
application/json
LLM
VLM
​
model
stringrequired
Corresponding Model Name. We periodically update our models to enhance service quality. Changes may include model on/offlining or capability adjustments. We will strive to notify you via announcements or push messages. For a complete list of available models, please check the Models.

Example:
"Pro/zai-org/GLM-4.7"

​
messages
object[]required
A list of messages comprising the conversation so far.

Required array length: 1 - 10 elements
Show child attributes

​
stream
boolean
If set, tokens are returned as Server-Sent Events as they are made available. Stream terminates with data: [DONE]

Example:
false

​
max_tokens
integer
The maximum number of tokens to generate. Ensure that input tokens + max_tokens do not exceed the model’s context window. As some services are still being updated, avoid setting max_tokens to the window’s upper bound; reserve ~10k tokens as buffer for input and system overhead. See Models(https://cloud.siliconflow.cn/models) for details.

Example:
4096

​
enable_thinking
boolean
Switches between thinking and non-thinking modes. This field supports the following models:

- Pro/zai-org/GLM-5
- Pro/zai-org/GLM-4.7
- deepseek-ai/DeepSeek-V3.2
- Pro/deepseek-ai/DeepSeek-V3.2
- zai-org/GLM-4.6
- Qwen/Qwen3-8B
- Qwen/Qwen3-14B
- Qwen/Qwen3-32B
- Qwen/Qwen3-30B-A3B
- tencent/Hunyuan-A13B-Instruct
- zai-org/GLM-4.5V
- deepseek-ai/DeepSeek-V3.1-Terminus
- Pro/deepseek-ai/DeepSeek-V3.1-Terminus        
- Qwen/Qwen3.5-397B-A17B
- Qwen/Qwen3.5-122B-A10B
- Qwen/Qwen3.5-35B-A3B
- Qwen/Qwen3.5-27B
- Qwen/Qwen3.5-9B
- Qwen/Qwen3.5-4B
Example:
false

​
thinking_budget
integer
Maximum number of tokens for chain-of-thought output. This field applies to most Reasoning models.

Required range: 128 <= x <= 32768
Example:
4096

​
reasoning_effort
enum<string>
This field only applies to deepseek-ai/DeepSeek-V4-Flash.
In thinking mode, the default effort for regular requests is high; for certain complex agent-type requests (such as Claude Code, OpenCode), the effort is automatically set to max.
In thinking mode, for compatibility reasons, low and medium are mapped to high, and xhigh is mapped to max.

Available options: high, max 
Example:
"high"

​
min_p
number<float>
Dynamic filtering threshold that adapts based on token probabilities.This field only applies to Qwen3.

Required range: 0 <= x <= 1
Example:
0.05

​
stop

string
string
Up to 4 sequences where the API will stop generating further tokens. The returned text will not contain the stop sequence.

Example:
null

​
temperature
number<float>
Determines the degree of randomness in the response.

Example:
0.7

​
top_p
number<float>default:0.7
The top_p (nucleus) parameter is used to dynamically adjust the number of choices for each predicted token based on the cumulative probabilities.

Example:
0.7

​
top_k
number<float>
Example:
50

​
frequency_penalty
number<float>
Example:
0.5

​
n
integer
Number of generations to return

Example:
1

​
response_format
object
An object specifying the format that the model must output.

Show child attributes

​
tools
object[]
A list of tools the model may call. Currently, only functions are supported as a tool. Use this to provide a list of functions the model may generate JSON inputs for. A max of 128 functions are supported.

Show child attributes

Response

200

application/json
The response from the model. The response header contains the x-siliconcloud-trace-id field, which serves as a unique identifier for tracing requests, facilitating log queries and issue troubleshooting.

​
id
string
​
choices
object[]
Show child attributes

​
usage
object
Show child attributes

​
created
integer
​
model
string
​
object
enum<string>
Available options: chat.completion 
```
curl --request POST \
  --url https://api.siliconflow.cn/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "Pro/zai-org/GLM-4.7",
    "messages": [
      {"role": "system", "content": "你是一个有用的助手"},
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ]
  }'


{
  "id": "019bdaa55225ef854b320e9b838f77ce",
  "object": "chat.completion",
  "created": 1768899826,
  "model": "Pro/zai-org/GLM-4.7",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！...",
        "reasoning_content": "..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 1540,
    "total_tokens": 1555,
    "completion_tokens_details": {
      "reasoning_tokens": 1190
    },
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 15
  },
  "system_fingerprint": ""
}
```

# 创建嵌入请求
创建嵌入请求
Converts input content into embedding vectors. Supports text, image URL/base64, and mixed lists.

POST
/
embeddings
Documentation Index
Fetch the complete documentation index at: https://docs.siliconflow.cn/llms.txt

Use this file to discover all available pages before exploring further.

Authorizations
​
Authorization
stringheaderrequired
Use the following format for authentication: Bearer

Body
application/json
EmbeddingsClassicRequest
EmbeddingsVLRequest
Compatible with two request formats:

Classic Embedding: keeps the historical parameter definition
VL Embedding: supports mixed text/image input, plus user and truncate
Note: OpenAPI cannot automatically route schemas based on model. Choose parameters according to model capabilities.

​
model
stringrequired
Corresponding Model Name. To better enhance service quality, we will make periodic changes to the models provided by this service, including but not limited to model on/offlining and adjustments to model service capabilities. We will notify you of such changes through appropriate means such as announcements or message pushes where feasible. For a complete list of available models, please check the Models.

Example:
"BAAI/bge-large-zh-v1.5"

​
input

string
string
required
Input text to embed must be provided as a string or an array of tokens. To process multiple inputs in a single request, pass an array of strings or an array of token arrays. The input length must not exceed the model's maximum token limit and should not be an empty string.
The maximum input tokens for each model are as follows:

BAAI/bge-large-zh-v1.5, BAAI/bge-large-en-v1.5, netease-youdao/bce-embedding-base_v1: 512
BAAI/bge-m3, Pro/BAAI/bge-m3: 8192
Qwen/Qwen3-Embedding-8B, Qwen/Qwen3-Embedding-4B, Qwen/Qwen3-Embedding-0.6B: 32768

Example:
"Silicon flow embedding online: fast, affordable, and high-quality embedding services. come try it out!"

​
encoding_format
enum<string>default:float
"The format to return the embeddings in. Can be either float or base64. "

Available options: float, base64 
Example:
"float"

​
dimensions
integer
The number of dimensions the resulting output embeddings should have. Only supported in Qwen/Qwen3 series. - Qwen/Qwen3-Embedding-8B: [64,128,256,512,768,1024,1536,2048,2560,4096] - Qwen/Qwen3-Embedding-4B:[64,128,256,512,768,1024,1536,2048,2560] - Qwen/Qwen3-Embedding-0.6B: [64,128,256,512,768,1024]

Example:
1024

Response

200

application/json
The response from the model. The response header contains the x-siliconcloud-trace-id field, which serves as a unique identifier for tracing requests, facilitating log queries and issue troubleshooting.

​
object
enum<string>required
The object type, which is always "list".

Available options: list 
​
model
stringrequired
The name of the model used to generate the embedding.

​
data
object[]required
The list of embeddings generated by the model.

Show child attributes

​
usage
objectrequired
The usage information for the request.

Show child attributes
```
curl -X POST https://api.siliconflow.cn/v1/embeddings \
  -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Hello, world!",
    "model": "Qwen/Qwen3-VL-Embedding-8B"
  }'


{
  "model": "<string>",
  "data": [
    {
      "embedding": [
        123
      ],
      "index": 123
    }
  ],
  "usage": {
    "prompt_tokens": 123,
    "completion_tokens": 123,
    "total_tokens": 123
  }
}
```

# 创建重排序请求
Reranks documents by relevance to a query. Supports text, image, and video content.

POST
/
rerank
Documentation Index
Fetch the complete documentation index at: https://docs.siliconflow.cn/llms.txt

Use this file to discover all available pages before exploring further.

Authorizations
​
Authorization
stringheaderrequired
Use the following format for authentication: Bearer

Body
application/json
RerankClassicRequest
RerankVLRequest
Compatible with two request formats:

Classic Rerank: text query with text documents
Multimodal Rerank: supports image/video content in query and documents
Note: OpenAPI cannot automatically route schemas based on model. Choose parameters according to model capabilities.

​
model
stringrequired
Corresponding Model Name. To better enhance service quality, we will make periodic changes to the models provided by this service, including but not limited to model on/offlining and adjustments to model service capabilities. We will notify you of such changes through appropriate means such as announcements or message pushes where feasible. For a complete list of available models, please check the Models.

Example:
"BAAI/bge-reranker-v2-m3"

​
query
stringrequired
The search query. Length must be ≥ 1.

Minimum string length: 1
Example:
"Apple"

​
documents

string
string
required
The list of documents to be ranked. Supports the following formats:

A single text string
An array of text strings At least 1 document is required.
Example:
"apple"

​
instruction
string
The instruction for the reranker. Only supported by Qwen/Qwen3-Reranker-8B, Qwen/Qwen3-Reranker-4B, Qwen/Qwen3-Reranker-0.6B. Length must be ≥ 1.

Minimum string length: 1
Example:
"Please rerank the documents based on the query."

​
top_n
integer
Number of most relevant documents or indices to return. Must be ≥ 1.

Required range: x >= 1
Example:
4

​
return_documents
booleandefault:false
If false, the response does not include document text; if true, it includes the input document text. Default is false.

​
max_chunks_per_doc
integerdefault:1024
Maximum number of chunks generated from within a document. Long documents are divided into multiple chunks for calculation, and the highest score among the chunks is taken as the document's score. Only BAAI/bge-reranker-v2-m3, Pro/BAAI/bge-reranker-v2-m3, netease-youdao/bce-reranker-base_v1 support this field. Must be ≥ 1, default is 1024.

Required range: x >= 1
​
overlap_tokens
integer
Number of token overlaps between adjacent chunks when documents are chunked. Only BAAI/bge-reranker-v2-m3, Pro/BAAI/bge-reranker-v2-m3, netease-youdao/bce-reranker-base_v1 support this field. Must be between 0 and 80.

Required range: 0 <= x <= 80
Response

200

application/json
The response from the model. The response header contains the x-siliconcloud-trace-id field, which serves as a unique identifier for tracing requests, facilitating log queries and issue troubleshooting.

​
id
stringrequired
Unique identifier for the response.

Example:
"rerank-20240115-abc123def456"

​
results
object[]required
List of reranked results sorted by relevance score.

Show child attributes

​
meta
object
Metadata about the rerank response.

Show child attributes
```
curl -X POST https://api.siliconflow.cn/v1/rerank \
  -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "BAAI/bge-reranker-v2-m3",
    "query": "Apple",
    "documents": ["apple", "banana", "fruit", "vegetable"],
    "return_documents": true,
    "top_n": 4
  }'

{
  "id": "rerank-20240115-abc123def456",
  "results": [
    {
      "index": 1,
      "document": {
        "text": "深度学习是机器学习的子集..."
      },
      "relevance_score": 0.85
    }
  ],
  "meta": {
    "tokens": {
      "input_tokens": 150,
      "output_tokens": 10,
      "image_tokens": 0
    },
    "billed_units": {
      "input_tokens": 150,
      "output_tokens": 10,
      "image_tokens": 0,
      "search_units": 1,
      "classifications": 0
    }
  }
}
```