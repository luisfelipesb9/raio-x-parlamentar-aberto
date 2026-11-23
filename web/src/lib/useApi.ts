"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGetUrl, apiUrl, type Params } from "./api";

export type Estado<T> =
  | { status: "ocioso" }
  | { status: "carregando" }
  | { status: "ok"; data: T }
  | { status: "erro"; erro: ApiError };

type Resultado<T> = { url: string; ok: true; data: T } | { url: string; ok: false; erro: ApiError };

/**
 * GET na API com estados explícitos (ocioso/carregando/ok/erro).
 * `path = null` deixa o hook ocioso (consulta condicional). O estado "carregando" é derivado
 * (resultado de outra URL = ainda carregando), sem setState síncrono dentro de efeito.
 */
export function useApi<T>(path: string | null, params?: Params): { estado: Estado<T>; recarregar: () => void } {
  const url = path === null ? null : apiUrl(path, params);
  const [resultado, setResultado] = useState<Resultado<T> | null>(null);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    if (url === null) return;
    const ac = new AbortController();
    apiGetUrl<T>(url, ac.signal)
      .then((data) => setResultado({ url, ok: true, data }))
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setResultado({ url, ok: false, erro: e instanceof ApiError ? e : new ApiError("interno", 0, null) });
      });
    return () => ac.abort();
  }, [url, tentativa]);

  const recarregar = useCallback(() => {
    setResultado(null);
    setTentativa((t) => t + 1);
  }, []);

  let estado: Estado<T>;
  if (url === null) estado = { status: "ocioso" };
  else if (resultado === null || resultado.url !== url) estado = { status: "carregando" };
  else estado = resultado.ok ? { status: "ok", data: resultado.data } : { status: "erro", erro: resultado.erro };
  return { estado, recarregar };
}
