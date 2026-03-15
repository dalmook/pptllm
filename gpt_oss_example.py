"""
GPT-OSS API 테스트 코드
"""
import requests
import json
import uuid

# API 설정
API_BASE_URL = 'http://apigw.samsungds.net:8000/gpt-oss/1/gpt-oss-120b/v1/chat/completions'

#Credential (사용자가 제공한 credential)
CREDENTIAL_KEY = 'credential:TICKET-96f7bce0-efab-4516-8e62-5501b07ab43c:ST0000107488-PROD:CTXLCkSDRGWtI5HdVHkPAQgol2o-RyQiq2I1vCHHOgGw:-1:Q1RYTENrU0RSR1d0STVIZFZIa1BBUWdvbDJvLVJ5UWlxMkkxdkNISE9nR3c=:signature=eRa1UcfmWGfKTDBt-Xnz2wFhW0OvMX0WESZUpoNVgCA5uNVgpgax59LZ3osPOp8whnZwQay8s5TUvxJGtmsCD9iK-HpcsyUOcE5P58W0Weyg-YQ3KRTWFiA=='

# 사용자 설정 (AD ID로 변경 필요)
USER_ID = 'sungmook.cho'  # 실제 AD ID로 변경
USER_TYPE = 'AD_ID'  # 고정값
SEND_SYSTEM_NAME = 'GOC_MAIL_RAG_PIPELINE'  # 승인받은 시스템 이름

def call_gpt_oss(prompt: str, system_prompt: str = None, temperature: float = 0.5, max_tokens: int = 500):
    """
    GPT-OSS API 호출
    
    Args:
        prompt: 사용자 입력 메시지
        system_prompt: 시스템 프롬프트 (선택)
        temperature: 생성 다양성 (0~1)
        max_tokens: 최대 생성 토큰 수
    
    Returns:
        dict: API 응답
    """
    # 메시지 구성
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # 페이로드
    payload = json.dumps({
        "model": "openai/gpt-oss-120b",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    })
    
    # 헤더
    headers = {
        'x-dep-ticket': CREDENTIAL_KEY,
        'Send-System-Name': SEND_SYSTEM_NAME,
        'User-Id': USER_ID,
        'User-Type': USER_TYPE,
        'Prompt-Msg-Id': str(uuid.uuid4()),
        'Completion-Msg-Id': str(uuid.uuid4()),
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # API 호출
    try:
        response = requests.post(
            API_BASE_URL, 
            headers=headers, 
            data=payload, 
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def main():
    print("=" * 50)
    print("GPT-OSS API 테스트")
    print("=" * 50)
    
    # 간단한 테스트
    print("\n[테스트 1] 간단한 인사")
    result = call_gpt_oss("안녕하세요!")
    
    if "error" in result:
        print(f"오류: {result['error']}")
    else:
        print(f"응답: {result['choices'][0]['message']['content']}")
        print(f"사용된 토큰: {result['usage']['total_tokens']}")
    
    # 시스템 프롬프트 포함 테스트
    print("\n[테스트 2] 파일리언 챗봇")
    result = call_gpt_oss(
        prompt="점심 뭐 드실 건가요?",
        system_prompt="당신은 친절한 파일리언 챗봇입니다. 모든 답변을 파일리언 목소리로 답하세요."
    )
    
    if "error" in result:
        print(f"오류: {result['error']}")
    else:
        print(f"응답: {result['choices'][0]['message']['content']}")
        print(f"사용된 토큰: {result['usage']['total_tokens']}")
    
    print("\n" + "=" * 50)
    print("테스트 완료")
    print("=" * 50)


if __name__ == "__main__":
    main()
