<script>
    // 추후 로그인/회원가입 구현 가능하도록 미리 만들어 둠
    //https://github.com/faulander/fastapi-sveltekit-template
	import { goto } from '$app/navigation';

	let email = '';
	let password = '';
	let error = '';

	async function handleSubmit() {
		const response = await fetch('http://localhost:8000/register', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded'
			},
			body: new URLSearchParams({
				username: email,
				password: password
			})
		});

		if (response.ok) {
			goto('/login');
		} else {
			const data = await response.json();
			error = data.detail || 'Registration failed';
		}
	}
</script>

<div class="bg-gray-100 flex items-center justify-center min-h-screen">
	<div class="bg-white p-8 rounded-lg shadow-lg w-96">
		<h1 class="text-2xl font-bold text-center mb-6">Register</h1>

		<form on:submit|preventDefault={handleSubmit}>
			<div class="mb-4">
				<label for="email" class="block text-sm font-medium text-gray-700">Email:</label>
				<input
					type="email"
					id="email"
					bind:value={email}
					required
					class="mt-1 block w-full border border-gray-300 rounded-md p-2 focus:ring-blue-500 focus:border-blue-500"
					placeholder="you@example.com"
				/>
			</div>
			<div class="mb-6">
				<label for="password" class="block text-sm font-medium text-gray-700">Password:</label>
				<input
					type="password"
					id="password"
					bind:value={password}
					required
					class="mt-1 block w-full border border-gray-300 rounded-md p-2 focus:ring-blue-500 focus:border-blue-500"
					placeholder="Your password"
				/>
			</div>
			{#if error}
				<div class="mb-2 items-center flex justify-center text-sm text-red-700">{error}</div>
			{/if}
			<button
				type="submit"
				class="w-full bg-blue-600 text-white font-semibold py-2 rounded-md hover:bg-blue-700 transition duration-200"
				>Register</button
			>
		</form>
		<div class="mt-2 items-center flex justify-center text-sm text-gray-400">
			Already have an account?&nbsp; <a href="/login" class="text-blue-400 hover:text-blue-700">
				Login here</a
			>
		</div>
	</div>
</div>
