import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Simulate from './pages/Simulate'
import Checkpoint from './pages/Checkpoint'
import MapPage from './pages/Map'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/simulate" element={<Simulate />} />
        <Route path="/checkpoint" element={<Checkpoint />} />
        <Route path="/map" element={<MapPage />} />
      </Route>
    </Routes>
  )
}
