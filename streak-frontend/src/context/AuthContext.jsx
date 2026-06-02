import { createContext, useContext, useEffect, useState } from 'react';

import { api, clearStoredAuth, getStoredUser, setStoredAuth } from '../api/axios';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredUser());

  useEffect(() => {
    if (!user) {
      const storedUser = getStoredUser();
      if (storedUser) {
        setUser(storedUser);
      }
    }
  }, [user]);

  const login = async ({ username, password }) => {
    const { data } = await api.post('/auth/login/', { username, password });
    const nextUser = { username };

    setStoredAuth({ ...data, user: nextUser });
    setUser(nextUser);

    return data;
  };

  const register = async ({ username, email, password }) => {
    const { data } = await api.post('/auth/register/', { username, email, password });
    const nextUser = data.user || { username, email };

    setStoredAuth({ ...data, user: nextUser });
    setUser(nextUser);

    return data;
  };

  const logout = () => {
    clearStoredAuth();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        register,
        logout,
        isAuthenticated: Boolean(user && localStorage.getItem('streak_access_token')),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}