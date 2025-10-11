// https://mycodings.fly.dev/blog/2023-08-09-user-authentication-system-in-svetlekit
// 로그아웃 로직 넣어 둠 (쿠키 삭제 후 로그인 페이지로 리다이렉트)
import { redirect } from '@sveltejs/kit'
import type { Actions } from './$types'
import type { PageServerLoad } from './$types'

export const load: PageServerLoad = async () => {
  throw redirect(302, '/')
}

export const actions: Actions = {
  default({ cookies }) {
    cookies.set('my-session', '', {
      path: '/',
      expires: new Date(0),
    })
    // redirect
    throw redirect(302, '/login')
  },
}