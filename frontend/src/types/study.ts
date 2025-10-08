export interface StudySummary {
    id: string; // 각 연구의 고유 ID (라우팅 파라미터)
    title: string;
    last_updated: string;
}

export interface StudyMessage {
    role: 'user' | 'assistant';
    text: string;
}

export interface StudyDetail extends StudySummary {
    messages: StudyMessage[];
}