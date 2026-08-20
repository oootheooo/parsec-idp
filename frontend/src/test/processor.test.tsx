import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {describe,expect,it,vi} from 'vitest'
import {api} from '../api/client'
import {ProcessorEditorPage} from '../pages/ProcessorEditorPage'
vi.mock('../api/client',()=>({api:vi.fn()}))
vi.mocked(api).mockResolvedValue([])
describe('processor editor',()=>{it('provides raw JSON Schema editing and publish-safe draft action',async()=>{const client=new QueryClient();render(<MemoryRouter><QueryClientProvider client={client}><ProcessorEditorPage/></QueryClientProvider></MemoryRouter>);expect((await screen.findByLabelText('JSON Schema') as HTMLTextAreaElement).value).toContain('"type": "object"');expect(screen.getByRole('button',{name:'Save draft'})).toBeInTheDocument();expect(screen.queryByRole('button',{name:/Publish/})).not.toBeInTheDocument()})})
