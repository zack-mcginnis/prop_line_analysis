import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Movements from './pages/Movements'
import Analysis from './pages/Analysis'
import Players from './pages/Players'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/movements" element={<Movements />} />
        <Route path="/analysis" element={<Analysis />} />
        <Route path="/players" element={<Players />} />
      </Routes>
    </Layout>
  )
}

export default App

