import { createContext, useContext, useState } from 'react'

const NavigationContext = createContext({
  isMobileOpen: false,
  toggleMobile: () => {},
  closeMobile: () => {},
})

export function NavigationProvider({ children }) {
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  return (
    <NavigationContext.Provider
      value={{
        isMobileOpen,
        toggleMobile: () => setIsMobileOpen((prev) => !prev),
        closeMobile: () => setIsMobileOpen(false),
      }}
    >
      {children}
    </NavigationContext.Provider>
  )
}

export function useNavigation() {
  return useContext(NavigationContext)
}

