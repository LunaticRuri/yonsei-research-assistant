<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import Header from '$lib/components/Header.svelte';
	let { children } = $props();
	let isLoggedIn = false; // 추후 로그인 상태에 따라 변경, 일단은 로그인된 상태로 취급
	let token: string | null = null;
	if (typeof window !== 'undefined') {
		token = localStorage.getItem('token');
		//isLoggedIn = token !== null;
		isLoggedIn = true; // 테스트용으로 항상 로그인된 상태로 설정
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<Header {isLoggedIn} />

{@render children?.()}
