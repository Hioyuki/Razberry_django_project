import os
import sys
import site

def fix():
    # venv??site-packages???
    sp = [p for p in sys.path if 'site-packages' in p and 'venv' in p][0]
    target_dir = os.path.join(sp, 'face_recognition')
    model_dir = os.path.join(sp, 'face_recognition_models', 'models')
    
    # ?????????
    api_file = os.path.join(target_dir, 'api.py')
    
    if os.path.exists(api_file):
        with open(api_file, 'r') as f:
            content = f.read()
        
        # ?????????????????????????????
        old_code = "import face_recognition_models"
        new_code = f"import face_recognition_models\nface_recognition_models.models = lambda: '{model_dir}'"
        
        if old_code in content and "lambda" not in content:
            with open(api_file, 'w') as f:
                f.write(content.replace(old_code, new_code))
            print("Successfully patched face_recognition for Python 3.13!")
        else:
            print("Already patched or target not found.")

if __name__ == "__main__":
    fix()
