"use client";

import Link from "next/link";
import { useEffect } from "react";

/** Falha ao carregar a ficha (API fora do ar, por exemplo). Não mostra detalhe técnico ao leitor. */
export default function ErroFicha({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    // o Next só entrega ao navegador uma mensagem genérica e o `digest`, que casa com o log do servidor
    console.error(error);
  }, [error]);

  return (
    <div className="pagina">
      <div className="estado estado-erro" role="alert">
        <h1 className="estado-titulo">Não deu para carregar esta ficha</h1>
        <p>Algo deu errado do nosso lado ou o servidor de dados está indisponível. Isso não diz nada sobre o deputado. Tente de novo em instantes.</p>
        <div className="acoes">
          <button type="button" className="btn" onClick={() => retry()}>
            Tentar de novo
          </button>
          <Link className="btn btn-sec" href="/deputados">
            Ver a lista de deputados
          </Link>
        </div>
      </div>
    </div>
  );
}
