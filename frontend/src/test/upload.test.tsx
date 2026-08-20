import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {MemoryRouter} from 'react-router-dom'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {api} from '../api/client'
import {UploadPage} from '../pages/UploadPage'
vi.mock('../api/client',()=>({api:vi.fn()}))
const mocked=vi.mocked(api)
describe('upload form',()=>{beforeEach(()=>mocked.mockResolvedValue({items:[],page:1,page_size:25,total:0,pages:0}));it('accepts a supported file and enables processing',async()=>{const client=new QueryClient({defaultOptions:{queries:{retry:false}}});const{container}=render(<MemoryRouter><QueryClientProvider client={client}><UploadPage/></QueryClientProvider></MemoryRouter>);const input=container.querySelector('input[type="file"]') as HTMLInputElement;await userEvent.upload(input,new File(['hello'],'invoice.pdf',{type:'application/pdf'}));expect(await screen.findByText('invoice.pdf')).toBeInTheDocument();expect(screen.getByRole('button',{name:'Upload and process'})).toBeEnabled()})})

