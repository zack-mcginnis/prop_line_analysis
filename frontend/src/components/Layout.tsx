import { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen grid-bg">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-dark-700 bg-dark-950/80 backdrop-blur-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center">
                <span className="text-white font-bold text-xl">P</span>
              </div>
              <div>
                <h1 className="font-display font-bold text-lg text-white">PropLine</h1>
                <p className="text-xs text-dark-400">Movement Analysis</p>
              </div>
            </div>

            {/* Status Badge */}
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
              <span className="text-sm text-dark-300">Live Tracking</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-dark-700 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-dark-400 text-sm">
            PropLine Movement Analysis • NFL Player Props Research
          </p>
        </div>
      </footer>
    </div>
  )
}
