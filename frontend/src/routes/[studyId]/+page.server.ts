import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import type { StudyDetail } from '../../types/study';

// 실제 사용자의 ID를 가져오는 함수 (인증 시스템에서 구현해야 함)
function getUserId(): string {
    return 'user123'; 
}

export const load: PageServerLoad = async ({ fetch, params }) => {
    const { studyId } = params;
    const user_id = getUserId();

    // FastAPI 엔드포인트에 연구 ID와 사용자 ID를 함께 전달
    const response = await fetch(`/api/studies/${studyId}?user_id=${user_id}`);

    if (!response.ok) {
        // 대화가 없거나(404) 접근 권한이 없을 경우
        throw error(response.status, '대화 내용을 불러올 수 없습니다.');
    }

    const study: StudyDetail = await response.json();
    
    return {
        study: study
    };
};