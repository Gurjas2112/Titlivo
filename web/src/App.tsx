import { createBrowserRouter, RouterProvider } from 'react-router'
import Layout from './components/Layout'
import Admin from './routes/Admin'
import Developers from './routes/Developers'
import Home from './routes/Home'
import Parcel from './routes/Parcel'
import Verifier from './routes/Verifier'
import Verify from './routes/Verify'

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <Home /> },
      { path: '/p/:parcelId', element: <Parcel /> },
      { path: '/v/:passportId', element: <Verifier /> },
      { path: '/verify', element: <Verify /> },
      { path: '/developers', element: <Developers /> },
      { path: '/admin', element: <Admin /> },
      { path: '*', element: <p className="p-8 text-slate-500">Page not found.</p> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
