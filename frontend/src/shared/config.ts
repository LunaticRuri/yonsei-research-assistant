// SvelteKit이 제공하는 $env 모듈을 사용하여 환경 변수를 가져옵니다.
import { env } from '$env/dynamic/private'; // 서버 측 환경 변수 접근

/**
 * 프로젝트 전체에서 사용되는 환경 설정 객체
 */
export const config = {
    // API 주소는 서버 환경 변수에서 가져옵니다.
    // .env 파일에 정의된 API_BASE_URL 변수를 사용합니다.
    apiBaseUrl: env.API_BASE_URL,
    
    // 필요하다면 다른 설정 값도 추가할 수 있습니다.
    // exampleSetting: 'default value',
};