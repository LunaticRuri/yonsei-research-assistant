<script>
  // 기본적인 프론트엔드 구조만 제공
  // 실제 구현은 다른 팀원이 담당
  let currentStep = 1; // 1: 대화, 2: 전략, 3: 분석, 4: 검색
</script>

<main>
  <header>
    <h1>수리조교</h1>
    <p>연세대학교 학술 연구 보조 AI</p>
  </header>

  <div class="container">
    {#if currentStep === 1}
      <div class="dialogue-panel">
        <h2>연구 주제 탐색</h2>
        <!-- 소크라테스식 대화 컴포넌트 -->
      </div>
    {:else if currentStep === 2}
      <div class="strategy-panel">
        <h2>검색 전략 수립</h2>
        <!-- 전략 캔버스 컴포넌트 -->
      </div>
    {:else if currentStep === 3}
      <div class="analysis-panel">
        <h2>RAG 분석</h2>
        <!-- 분석 워크벤치 컴포넌트 -->
      </div>
    {:else if currentStep === 4}
      <div class="search-panel">
        <h2>도서관 검색 결과</h2>
        <!-- 검색 결과 컴포넌트 -->
      </div>
    {/if}
  </div>
</main>

<style>
  /* 기본 스타일만 제공 */
  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
  }
  
  .container {
    display: flex;
    gap: 20px;
    margin-top: 20px;
  }
</style>