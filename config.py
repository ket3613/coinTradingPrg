import yaml

def load_config(file_path="config.yml"):
    """YAML 파일에서 설정 로드"""
    with open(file_path, "r") as f:
        config = yaml.safe_load(f)
    return config
