<script lang="ts">
    import type { PageData } from './$types';
    export let data: PageData;
    export const studyId = data.study?.id;
</script>


{#if data.study}
    <div class="chat-header">
        <h1>{data.study.title}</h1>
        <p>연구 ID: {studyId}</p>
    </div>
    
    <div class="chat-window">
        {#each data.study.messages as message}
            <div class="message-row {message.role}">
                <div class="chat-bubble">
                    <div class="role-label">
                        {message.role === 'user' ? '나' : '수리조교 (AI)'}
                    </div>
                    <p>{message.text}</p>
                </div>
            </div>
        {/each}
        
        <div class="input-area">
            <input type="text" placeholder="메시지를 입력하세요..." />
            <button>전송</button>
        </div>
    </div>
{:else}
    <p>대화 내용을 불러오는 중...</p>
{/if}

<style>
    .chat-header {
        padding: 15px;
        border-bottom: 1px solid #ddd;
        margin-bottom: 20px;
    }
    .chat-window {
        display: flex;
        flex-direction: column;
        gap: 15px;
        padding: 0 20px 80px 20px; /* 입력창 공간 확보 */
    }

    /* === 메시지 행 스타일링 === */
    .message-row {
        display: flex;
    }
    
    /* 사용자 메시지는 오른쪽 정렬 */
    .message-row.user {
        justify-content: flex-end;
    }
    
    /* AI 메시지는 왼쪽 정렬 */
    .message-row.assistant {
        justify-content: flex-start;
    }

    /* === 말풍선 스타일링 === */
    .chat-bubble {
        max-width: 70%;
        padding: 10px 15px;
        border-radius: 20px;
        line-height: 1.5;
        position: relative;
        color: #333;
    }

    /* 사용자 말풍선 */
    .message-row.user .chat-bubble {
        background-color: #dcf8c6; /* 연한 녹색 */
        color: #000;
        border-bottom-right-radius: 4px; /* 끝을 뾰족하게 */
    }

    /* AI 말풍선 */
    .message-row.assistant .chat-bubble {
        background-color: #f0f0f0; /* 연한 회색 */
        border: 1px solid #e0e0e0;
        border-bottom-left-radius: 4px; /* 끝을 뾰족하게 */
    }
    
    .role-label {
        font-size: 0.8em;
        font-weight: bold;
        margin-bottom: 5px;
        opacity: 0.7;
    }
    
    /* === 입력 영역 스타일링 (ChatGPT처럼 하단 고정) === */
    .input-area {
        position: fixed; /* 뷰포트 하단에 고정 */
        bottom: 0;
        left: 0;
        right: 0;
        padding: 15px 20px;
        background-color: white;
        border-top: 1px solid #e0e0e0;
        display: flex;
        box-shadow: 0 -2px 5px rgba(0,0,0,0.05);
    }
    .input-area input[type="text"] {
        flex-grow: 1;
        padding: 10px;
        border: 1px solid #ccc;
        border-radius: 8px;
        margin-right: 10px;
        font-size: 1em;
    }
    .input-area button {
        padding: 10px 20px;
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
    }
</style>

<!-- <style>
    .new-study-button {
        padding: 10px 15px;
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        font-size: 1em;
        margin-bottom: 20px;
    }
    .new-study-button:hover {
        background-color: #0056b3;
    }
    ul { list-style: none; padding: 0; }
    li { margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    a { text-decoration: none; color: inherit; display: block; padding: 5px; }
    a:hover { background-color: #f0f0f0; }
    .empty-state {
        color: #888;
        padding-top: 20px;
        text-align: center;
    }
</style> -->