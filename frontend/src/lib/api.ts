type ApiOptions = RequestInit & {
  body?: BodyInit | null;
};

export async function apiFetch<T>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = (await response.json()) as T & {
    detail?: string | Array<{ msg?: string }>;
  };

  if (!response.ok) {
    let message = "The request could not be completed.";
    if (typeof payload.detail === "string") {
      message = payload.detail;
    } else if (Array.isArray(payload.detail)) {
      message = payload.detail
        .map((item) => item.msg)
        .filter(Boolean)
        .join(" ");
    }
    throw new Error(message);
  }

  return payload;
}
