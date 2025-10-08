import type { PageServerLoad, Actions } from './$types';
import type { StudySummary } from '../types/study';
import { error , fail, redirect } from '@sveltejs/kit';
// Update the import path to the correct location of your config file
import { config } from '../shared/config'; 

// 실제 사용자의 ID를 가져오는 함수 (인증 시스템에서 구현해야 함)
function getUserId(): string {
    // 실제로는 세션, 쿠키, JWT 토큰 등에서 사용자의 ID를 추출해야 합니다.
    // 여기서는 테스트를 위해 임시로 "user123"을 반환합니다.
    return 'user123'; 
}

export const load: PageServerLoad = async ({ fetch }) => {
    // 🌟 config에서 API 주소를 가져옵니다.
    const baseUrl = config.apiBaseUrl;
    
    // 만약 환경 변수가 설정되지 않았다면 오류를 발생시킵니다.
    if (!baseUrl) {
        throw error(500, 'API_BASE_URL 환경 변수가 설정되지 않았습니다.');
    }
    
    const user_id = getUserId();
    // 🌟 전체 URL을 사용하여 FastAPI 서버로 요청합니다.
    const response = await fetch(`${baseUrl}/api/studies?user_id=${user_id}`);

    if (!response.ok) {
        throw error(response.status, '대화 목록을 불러오는 데 실패했습니다.');
    }

    const studies: StudySummary[] = await response.json();
    
    return {
        studies: studies
    };
};

// 2. 새로운 연구 생성 액션 (POST) TODO 이후 라우트되도록 
export const actions: Actions = {
    newStudy: async ({ fetch }) => {
        const user_id = getUserId();
        const baseUrl = config.apiBaseUrl;
        
        try {
            // FastAPI 엔드포인트에 POST 요청
            const response = await fetch(`${baseUrl}/api/studies/new?user_id=${user_id}`, {
                method: 'POST', // 🌟 POST 메서드 사용
            });

            if (!response.ok) {
                return fail(response.status, {
                    message: '새 연구 생성에 실패했습니다.',
                });
            }

            // FastAPI에서 반환된 새로 생성된 대화 객체
            const newStudy: StudySummary = await response.json();

            // 성공 시 새로 생성된 연구의 상세 페이지로 리다이렉션
            throw redirect(303, `/studies/${newStudy.id}`);
            
        } catch (err) {
            console.error('New study creation error:', err);
            // SvelteKit의 redirect는 try/catch 내에서 throw해야 함
            if (err instanceof Error && 'status' in err) {
                throw err; 
            }
            return fail(500, { message: '서버 오류로 새 연구를 생성할 수 없습니다.' });
        }
    }
};

