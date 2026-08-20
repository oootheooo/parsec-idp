import {render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {MemoryRouter} from 'react-router-dom'
import {describe,expect,it} from 'vitest'
import {AuthProvider} from '../auth'
import {AuthPage} from '../pages/AuthPage'
describe('login form',()=>{it('shows validation before submitting invalid credentials',async()=>{render(<MemoryRouter initialEntries={['/login']}><AuthProvider><AuthPage/></AuthProvider></MemoryRouter>);await userEvent.type(screen.getByLabelText('Email'),'not-an-email');await userEvent.type(screen.getByLabelText('Password'),'short');await userEvent.click(screen.getByRole('button',{name:'Sign in'}));expect(await screen.findByText('Invalid email')).toBeInTheDocument();expect(screen.getByText('Use at least 10 characters')).toBeInTheDocument()})})

