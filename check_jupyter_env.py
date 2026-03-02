"""
诊断和修复 Jupyter notebook 环境问题
"""
import sys
import subprocess
import importlib.util

def check_package(package_name):
    """检查包是否已安装"""
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        return False, None
    return True, spec.origin

def main():
    print("="*60)
    print("Jupyter Environment Diagnostic")
    print("="*60)
    
    print(f"\n[INFO] Current Python path:")
    print(f"   {sys.executable}")
    
    print(f"\n[CHECK] Checking key dependencies:")
    packages = ['hmmlearn', 'yfinance', 'pandas', 'numpy', 'sklearn', 'matplotlib', 'seaborn', 'yaml', 'tqdm']
    
    missing = []
    for pkg in packages:
        installed, location = check_package(pkg)
        if installed:
            print(f"   [OK] {pkg:15s} - {location}")
        else:
            print(f"   [MISSING] {pkg:15s} - Not installed")
            missing.append(pkg)
    
    if missing:
        print(f"\n[WARNING] Missing packages: {', '.join(missing)}")
        print(f"\n[SOLUTION] Fix by running in Jupyter notebook:")
        print(f"   !pip install {' '.join(missing)}")
        print(f"\n   Or in command line:")
        print(f"   {sys.executable} -m pip install {' '.join(missing)}")
    else:
        print(f"\n[SUCCESS] All dependencies installed!")
    
    print(f"\n[CHECK] Jupyter kernel check:")
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'jupyter', 'kernelspec', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("   [WARNING] Cannot list kernels")
    except Exception as e:
        print(f"   [ERROR] {e}")
    
    print(f"\n[TIPS] If Jupyter still has errors:")
    print(f"   1. In notebook first cell, run:")
    print(f"      import sys")
    print(f"      print(sys.executable)")
    print(f"   2. Verify the path matches the Python path above")
    print(f"   3. If different, install ipykernel:")
    print(f"      {sys.executable} -m pip install ipykernel")
    print(f"   4. Then register kernel:")
    print(f"      {sys.executable} -m ipykernel install --user --name=thomas1")

if __name__ == '__main__':
    main()
