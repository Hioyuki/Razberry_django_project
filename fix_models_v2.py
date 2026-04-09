import os
import sys

# site-packages??????
sp = [p for p in sys.path if 'site-packages' in p and 'venv' in p][0]
api_file = os.path.join(sp, 'face_recognition', 'api.py')
model_dir = os.path.join(sp, 'face_recognition_models', 'models')

if os.path.exists(api_file):
    with open(api_file, 'r') as f:
        lines = f.readlines()

    with open(api_file, 'w') as f:
        for line in lines:
            f.write(line)
            # import??????????????????????????
            if "import face_recognition_models" in line:
                indent = line[:line.find("import")]
                f.write(f"{indent}face_recognition_models.models = lambda: '{model_dir}'\n")
    print("Successfully patched with correct indentation!")
