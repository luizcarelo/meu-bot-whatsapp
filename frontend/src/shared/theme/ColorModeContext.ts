import { createContext, useContext } from 'react';

export type ColorModeName = 'light' | 'dark';

export interface ColorModeContextValue {
  mode: ColorModeName;
  toggleMode: () => void;
}

export const ColorModeContext = createContext<ColorModeContextValue>({
  mode: 'light',
  toggleMode: () => undefined
});

export function useColorMode() {
  return useContext(ColorModeContext);
}
