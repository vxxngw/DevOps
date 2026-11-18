export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function request<T>(path: string, token = '', init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(path, { ...init, headers });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(
      'Chưa thể kết nối. Vui lòng thử lại; thông tin bạn đã chọn vẫn được giữ.',
      0,
    );
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      'Máy chủ tạm thời chưa sẵn sàng. Vui lòng thử lại sau ít phút.',
      response.status,
    );
  }
  if (!response.ok)
    throw new ApiError(
      typeof data.error?.message === 'string'
        ? data.error.message
        : 'Chưa thể hoàn tất yêu cầu. Vui lòng thử lại.',
      response.status,
    );
  return data as T;
}
