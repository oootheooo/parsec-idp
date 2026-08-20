import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {StrictMode} from 'react'
import {createRoot} from 'react-dom/client'
import {BrowserRouter} from 'react-router-dom'
import {App} from './App'
import {AuthProvider} from './auth'
import './index.css'
const client=new QueryClient({defaultOptions:{queries:{retry:1,staleTime:10_000}}})
createRoot(document.getElementById('root')!).render(<StrictMode><BrowserRouter><QueryClientProvider client={client}><AuthProvider><App/></AuthProvider></QueryClientProvider></BrowserRouter></StrictMode>)

