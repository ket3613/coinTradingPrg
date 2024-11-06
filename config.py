import yaml

def load_config(file_path):
    """주어진 경로의 YAML 파일을 읽고 설정 값을 반환합니다."""
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config
