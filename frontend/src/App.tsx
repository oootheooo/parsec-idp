import {Navigate,Route,Routes} from 'react-router-dom'
import {useAuth} from './auth'
import {AppShell} from './components/AppShell'
import {Loading} from './components/UI'
import {AuthPage} from './pages/AuthPage'
import {DashboardPage} from './pages/DashboardPage'
import {DeveloperPage} from './pages/DeveloperPage'
import {DocumentDetailPage} from './pages/DocumentDetailPage'
import {DocumentsPage} from './pages/DocumentsPage'
import {ProcessorEditorPage} from './pages/ProcessorEditorPage'
import {ProcessorsPage} from './pages/ProcessorsPage'
import {ReviewPage} from './pages/ReviewPage'
import {SettingsPage} from './pages/SettingsPage'
import {UploadPage} from './pages/UploadPage'
import {WorkflowsPage} from './pages/WorkflowsPage'
function Protected(){const{user,loading}=useAuth();if(loading)return <Loading label="Starting Parsec"/>;return user?<AppShell/>:<Navigate to="/login" replace/>}
export function App(){return <Routes><Route path="/login" element={<AuthPage/>}/><Route path="/register" element={<AuthPage/>}/><Route element={<Protected/>}><Route index element={<DashboardPage/>}/><Route path="documents" element={<DocumentsPage/>}/><Route path="documents/new" element={<UploadPage/>}/><Route path="documents/:id" element={<DocumentDetailPage/>}/><Route path="documents/:id/review" element={<ReviewPage/>}/><Route path="processors" element={<ProcessorsPage/>}/><Route path="processors/new" element={<ProcessorEditorPage/>}/><Route path="processors/:id" element={<Navigate to="edit" replace/>}/><Route path="processors/:id/edit" element={<ProcessorEditorPage/>}/><Route path="workflows" element={<WorkflowsPage/>}/><Route path="developer" element={<DeveloperPage/>}/><Route path="settings" element={<SettingsPage/>}/><Route path="settings/members" element={<SettingsPage/>}/></Route><Route path="*" element={<Navigate to="/" replace/>}/></Routes>}

