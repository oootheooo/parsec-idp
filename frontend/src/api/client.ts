const API_URL=import.meta.env.VITE_API_URL||'http://localhost:8000/api/v1'
let accessToken=localStorage.getItem('parsec_access')
let workspaceId=localStorage.getItem('parsec_workspace')
export const session={get token(){return accessToken},setToken(value:string|null){accessToken=value;if(value)localStorage.setItem('parsec_access',value);else localStorage.removeItem('parsec_access')},get workspace(){return workspaceId},setWorkspace(value:string|null){workspaceId=value;if(value)localStorage.setItem('parsec_workspace',value);else localStorage.removeItem('parsec_workspace')}}

async function refresh(){const response=await fetch(`${API_URL}/auth/refresh`,{method:'POST',credentials:'include'});if(!response.ok)return false;const data=await response.json();session.setToken(data.access_token);return true}

export async function api<T>(path:string,options:RequestInit={},retry=true):Promise<T>{
 const headers=new Headers(options.headers); if(accessToken)headers.set('Authorization',`Bearer ${accessToken}`);if(workspaceId)headers.set('X-Workspace-ID',workspaceId);if(options.body&&!(options.body instanceof FormData))headers.set('Content-Type','application/json')
 const response=await fetch(`${API_URL}${path}`,{...options,headers,credentials:'include'})
 if(response.status===401&&retry&&!path.startsWith('/auth/')&&await refresh())return api<T>(path,options,false)
 if(!response.ok){let message=`Request failed (${response.status})`;try{const body=await response.json();message=body.detail||body.error?.message||message}catch{/* empty */}throw new Error(message)}
 if(response.status===204)return undefined as T
 return response.json()
}
export {API_URL}
