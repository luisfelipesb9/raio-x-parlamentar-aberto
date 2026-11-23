import Link from "next/link";
import type { ReactNode } from "react";
import type { ApiError } from "@/lib/api";

export function Carregando({ texto = "Carregando…" }: { texto?: string }) {
  return (
    <div className="estado estado-carregando" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{texto}</span>
    </div>
  );
}

export function ErroApi({ erro, onTentarDeNovo, voltar }: { erro: ApiError; onTentarDeNovo?: () => void; voltar?: { href: string; texto: string } }) {
  const podeTentar = erro.tipo === "rede" || erro.tipo === "indisponivel" || erro.tipo === "interno";
  return (
    <div className="estado estado-erro" role="alert">
      <p className="estado-titulo">{erro.tipo === "nao_encontrado" ? "Não encontramos isto" : "Não deu para carregar"}</p>
      <p>{erro.mensagemParaLeigo}</p>
      <div className="acoes">
        {podeTentar && onTentarDeNovo && (
          <button type="button" className="btn" onClick={onTentarDeNovo}>
            Tentar de novo
          </button>
        )}
        {voltar && (
          <Link className="btn btn-sec" href={voltar.href}>
            {voltar.texto}
          </Link>
        )}
      </div>
    </div>
  );
}

export function Vazio({ titulo, children }: { titulo: string; children?: ReactNode }) {
  return (
    <div className="estado estado-vazio">
      <p className="estado-titulo">{titulo}</p>
      {children && <div>{children}</div>}
    </div>
  );
}
