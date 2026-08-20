/* eslint-disable react-refresh/only-export-components */
import {createContext,useCallback,useContext,useEffect,useMemo,useState,type ReactNode} from 'react'
import {api,session} from './api/client'
import type {User} from './types'
type AuthValue={user:User|null;loading:boolean;workspaceId:string|null;login:(email:string,password:string)=>Promise<void>;register:(data:Record<string,string>)=>Promise<void>;logout:()=>Promise<void>;switchWorkspace:(id:string)=>void;reload:()=>Promise<void>}
const AuthContext=createContext<AuthValue|null>(null)
export function AuthProvider({children}:{children:ReactNode}){const[user,setUser]=useState<User|null>(null);const[loading,setLoading]=useState(true);const[workspaceId,setWorkspaceId]=useState(session.workspace)
 const reload=async()=>{if(!session.token){setUser(null);setLoading(false);return}try{const next=await api<User>('/me');setUser(next);if(!session.workspace&&next.workspaces[0]){session.setWorkspace(next.workspaces[0].id);setWorkspaceId(next.workspaces[0].id)}}catch{session.setToken(null);setUser(null)}finally{setLoading(false)}}
 useEffect(()=>{void reload()},[])
 const authenticate=useCallback(async(path:string,data:Record<string,string>)=>{const result=await api<{access_token:string}>(path,{method:'POST',body:JSON.stringify(data)});session.setToken(result.access_token);await reload()},[])
 const value=useMemo<AuthValue>(()=>({user,loading,workspaceId,login:(email,password)=>authenticate('/auth/login',{email,password}),register:data=>authenticate('/auth/register',data),logout:async()=>{try{await api('/auth/logout',{method:'POST'})}finally{session.setToken(null);session.setWorkspace(null);setUser(null)}},switchWorkspace:id=>{session.setWorkspace(id);setWorkspaceId(id);location.reload()},reload}),[user,loading,workspaceId,authenticate])
 return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>}
export function useAuth(){const value=useContext(AuthContext);if(!value)throw new Error('AuthProvider missing');return value}
