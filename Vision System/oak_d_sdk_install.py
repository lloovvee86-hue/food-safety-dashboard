import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

print("--- [코다리 부장의 OAK-D S2 환경 설정 서비스] ---")

# 1. 필수 라이브러리 체크 및 설치
required_packages = ["depthai", "opencv-python"]

for package in required_packages:
    try:
        __import__(package.split('-')[0])
        print(f"[OK] {package} 가 이미 설치되어 있습니다.")
    except ImportError:
        print(f"[Wait] {package} 설치 중... 잠시만 기다려 주십시오, 대표님!")
        install(package)
        print(f"[OK] {package} 설치 완료!")

# 2. 장치 연결 확인 (가상 체크)
import depthai as dai

print("\n--- [장치 인식 테스트] ---")
devices = dai.Device.getAllAvailableDevices()

if not devices:
    print("⚠️  현재 연결된 OAK-D 장비를 찾을 수 없습니다.")
    print("👉 장비가 도착하면 USB-C 케이블로 PC에 연결한 후 다시 실행해 주십시오.")
    print("   (참고: USB 3.0 포트 사용을 권장합니다!)")
else:
    print(f"✅ 총 {len(devices)}개의 OAK-D 장치가 발견되었습니다!")
    for dev in devices:
        print(f" - 장치 ID: {dev.getMxId()}")

print("\n대표님, 기초 설정을 마쳤습니다! 이제 데이터만 준비되면 바로 시작할 수 있습니다. 충성! 😎🚀")
