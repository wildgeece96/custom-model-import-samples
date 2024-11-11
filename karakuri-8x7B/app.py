"""Streamlit でホストしたアプリで import したモデルを使ってみる
"""
import json
import logging
import time

import boto3
import streamlit as st
from botocore.config import Config
from botocore.exceptions import ClientError

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BedrockModelInvoker:
    def __init__(self, config):
        boto3_config = Config(
            retries={
                'total_max_attempts': config['max_retries'],
                'mode': 'standard'
            }
        )
        
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=config['region_name'],
            config=boto3_config
        )
        
        self.model_arn = config['model_arn']

    def invoke_model(self, prompt, max_tokens=100, temperature=0.7):
        try:
            request_body = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            start_time = time.time()
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_arn,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            end_time = time.time()
            
            response_body = json.loads(response['body'].read().decode('utf-8'))
            logger.info(f"Response time is {end_time - start_time:.3f} sec")
            
            # モデルの出力からJSON部分を抽出して解析
            try:
                if isinstance(response_body, str):
                    # 文字列からJSONを抽出（余分なテキストがある場合に対応）
                    import re
                    json_match = re.search(r'\{.*\}', response_body, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    else:
                        raise ValueError("JSON not found in response")
                else:
                    return response_body
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from response: {str(e)}")
                raise

        except ClientError as e:
            logger.error(f"Error invoking model: {str(e)}")
            raise

def create_prompt(names):
    """
    名前のリストからプロンプトを生成
    """
    names_list = "\n".join([f"- {name.strip()}" for name in names if name.strip()])
    
    prompt = f"""あなたは、抽選を行うロボットです。下記リストの中から、ランダムな形で人を選び、それを出力してください。
出力形式は下記のフォーマットのjsonでお願いします。jsonのみ出力してください。
[LIST]
{names_list}
[/LIST]
[FORMAT]
{{
  "name": {{
    "type": "string",
    "description": "抽選された人の名前（フルネーム）"
  }}
}}
[/FORMAT]"""
    
    return f"[INST]{prompt}[/INST]"


def parse_arguments():
    """コマンドライン引数のパース"""
    parser = argparse.ArgumentParser(
        description='Download a model from HuggingFace and upload it to S3'
    )
    
    parser.add_argument(
        '--model-arn',
        type=str,
        required=True,
        help='Imported Model ARN'
    )

    parser.add_argument(
        '--region',
        type=str,
        default='us-west-2',
        help='Region of imported model.'
    )
    
    
    return parser.parse_args()

def main():
    args = parse_arguments()
    st.set_page_config(
        page_title="抽選アプリ",
        page_icon="🎲",
        layout="wide"
    )

    st.title("🎲 名前抽選アプリ")
    st.markdown("## Powered by KARAKURI LM 8x7B Chat v0.1 ")
    st.markdown("### This model is hosted on **Amazon Bedrock Custom Model Import**.")
    
    # モデル設定
    model_config = {
        'region_name': args.region,
        'model_arn': args.model_arn,
        'max_retries': 30
    }

    # 名前入力エリア
    st.header("参加者名簿")
    names_text = st.text_area(
        "抽選対象者の名前を1行に1人ずつ入力してください",
        height=200,
        placeholder="例：\nアマゾン太郎\nジーニアック時子"
    )

    # 抽選実行ボタン
    if st.button("抽選開始! 🎯", type="primary"):
        if not names_text.strip():
            st.error("名前を入力してください")
            return

        names = [name for name in names_text.split('\n') if name.strip()]
        
        if len(names) < 1:
            st.error("少なくとも1人の名前を入力してください")
            return

        try:
            with st.spinner("抽選中..."):
                # プロンプトの生成と抽選実行
                prompt = create_prompt(names)
                invoker = BedrockModelInvoker(model_config)
                result = invoker.invoke_model(
                    prompt=prompt,
                    max_tokens=256,
                    temperature=0.7
                )

                # 結果の表示
                result_json = json.loads(result.get("outputs")[0].get("text"))
                if isinstance(result_json, dict) and 'name' in result_json:
                    st.balloons()  # 視覚効果
                    st.success("抽選が完了しました！")
                    
                    # 結果表示用のカード
                    st.markdown("""
                    <div style='padding: 20px; border-radius: 10px; background-color: #f0f2f6; text-align: center;'>
                        <h2 style='color: #0066cc;'>当選者</h2>
                        <h1 style='color: #333333;'>{}</h1>
                    </div>
                    """.format(result_json['name']), unsafe_allow_html=True)
                    st.markdown(f"LLM からの返答内容: {result}")
                    
                else:
                    st.error("抽選結果の解析に失敗しました")
                    logger.error(f"Unexpected response format: {result}")

        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")
            logger.error(f"Error during lottery: {str(e)}")

    # 使い方の説明
    with st.expander("💡 使い方"):
        st.markdown("""
        1. テキストエリアに抽選対象者の名前を1行に1人ずつ入力します
        2. 「抽選開始!」ボタンをクリックします
        3. AIが公平に抽選を行い、当選者を表示します
        
        注意事項：
        - 空行は自動的に無視されます
        - 名前は省略せずにフルネームで入力してください
        """)

if __name__ == "__main__":
    main()
