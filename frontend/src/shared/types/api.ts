export interface ApiError {
  code: string;
  message: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error: ApiError | null;
}

export interface LegacyStatusResponse {
  success: boolean;
  empresaId?: number;
  connected?: boolean;
  status?: string;
  qr?: string | null;
}
