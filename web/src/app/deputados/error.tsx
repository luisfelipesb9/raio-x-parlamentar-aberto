"use client";

import Link from "next/link";
import { useEffect } from "react";

/** Falha ao carregar a lista (API fora do ar, por exemplo). Sem detalhe técnico para o leitor. */
export default function ErroLista({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="pagina">
      <div className="estado estado-erro" role="alert">
        <h1 className="estado-titulo">Não deu para carregar a lista de deputados</h1>
        <p>O servidor de dados pode estar indisponível no momento. Tente de novo em instantes.</p>
        <div className="acoes">
          <button type="button" className="btn" onClick={() => retry()}>
            Tentar de novo
          </button>
          <Link className="btn btn-sec" href="/">
            Voltar ao início
          </Link>
        </div>
      </div>
    </div>
  );
}
