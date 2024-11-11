import os
import argparse
import subprocess
import boto3
from botocore.exceptions import ClientError
import shutil
import logging

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelDownloader:
    def __init__(self, model_id, bucket_name, local_path="./model"):
        """
        :param model_id: HuggingFace のモデル ID (例: 'karakuri-ai/karakuri-lm-8x7b-chat-v0.1')
        :param bucket_name: アップロード先の S3 バケット名
        :param local_path: モデルをダウンロードするローカルパス
        """
        self.model_id = model_id
        self.bucket_name = bucket_name
        self.local_path = local_path
        self.s3_client = boto3.client('s3')

    def check_git_lfs(self):
        """Git LFS がインストールされているか確認"""
        try:
            subprocess.run(['git', 'lfs', 'version'], check=True, capture_output=True)
            logger.info("Git LFS is installed")
            return True
        except subprocess.CalledProcessError:
            logger.error("Git LFS is not installed. Please install it first.")
            return False
        except FileNotFoundError:
            logger.error("Git is not installed. Please install Git and Git LFS.")
            return False

    def download_model(self):
        """モデルをダウンロード"""
        if not self.check_git_lfs():
            return False

        try:
            # 既存のディレクトリがあれば削除
            if os.path.exists(self.local_path):
                shutil.rmtree(self.local_path)

            # Git LFS pull でモデルをダウンロード
            logger.info(f"Cloning repository: {self.model_id}")
            subprocess.run([
                'git', 'clone',
                f'https://huggingface.co/{self.model_id}',
                self.local_path
            ], check=True)

            # Git LFS pull を実行
            subprocess.run([
                'git', 'lfs', 'pull'
            ], cwd=self.local_path, check=True)

            logger.info("Model downloaded successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Error during model download: {str(e)}")
            return False

    def upload_to_s3(self):
        """モデルを S3 にアップロード"""
        try:
            # モデルディレクトリ内のすべてのファイルをアップロード
            for root, _, files in os.walk(self.local_path):
                for file in files:
                    local_file_path = os.path.join(root, file)
                    # S3のキーを作成（ローカルパスの先頭部分を除去）
                    s3_key = os.path.relpath(local_file_path, self.local_path)
                    
                    logger.info(f"Uploading {s3_key} to S3...")
                    self.s3_client.upload_file(
                        local_file_path,
                        self.bucket_name,
                        f"karakuri-model/{s3_key}"
                    )

            logger.info("All files uploaded to S3 successfully")
            return True

        except ClientError as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            return False

    def cleanup(self):
        """ダウンロードしたファイルを削除"""
        try:
            if os.path.exists(self.local_path):
                shutil.rmtree(self.local_path)
                logger.info("Cleaned up local files")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


def parse_arguments():
    """コマンドライン引数のパース"""
    parser = argparse.ArgumentParser(
        description='Download a model from HuggingFace and upload it to S3'
    )
    
    parser.add_argument(
        '--model-id',
        type=str,
        default="karakuri-ai/karakuri-lm-8x7b-chat-v0.1",
        help='HuggingFace model ID (default: karakuri-ai/karakuri-lm-8x7b-chat-v0.1)'
    )
    
    parser.add_argument(
        '--bucket',
        type=str,
        required=True,
        help='S3 bucket name for upload'
    )
    
    parser.add_argument(
        '--local-path',
        type=str,
        default="./karakuri-model",
        help='Local path for temporary model storage (default: ./karakuri-model)'
    )
    
    parser.add_argument(
        '--s3-prefix',
        type=str,
        default="karakuri-model",
        help='S3 prefix for uploaded files (default: karakuri-model)'
    )
    
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Do not clean up local files after upload'
    )
    
    return parser.parse_args()

def main():
    # コマンドライン引数のパース
    args = parse_arguments()
    
    # ダウンローダーのインスタンスを作成
    downloader = ModelDownloader(
        model_id=args.model_id,
        bucket_name=args.bucket,
        local_path=args.local_path
    )
    
    try:
        # モデルをダウンロード
        if not downloader.download_model():
            raise Exception("Model download failed")
        
        # S3 にアップロード
        if not downloader.upload_to_s3(s3_prefix=args.s3_prefix):
            raise Exception("S3 upload failed")
        
        logger.info("Process completed successfully")
    
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        raise
    
    finally:
        # クリーンアップ（--no-cleanup が指定されていない場合）
        if not args.no_cleanup:
            downloader.cleanup()


if __name__ == "__main__":
    main()
