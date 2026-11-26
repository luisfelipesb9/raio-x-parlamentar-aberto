import Link from "next/link";

/** 404 real (status HTTP 404) para ids que a API não conhece. Mesmo desenho do estado de erro do restante do site. */
export default function DeputadoNaoEncontrado() {
  return (
    <div className="pagina">
      <div className="estado estado-erro" role="alert">
        <h1 className="estado-titulo">Deputado não encontrado</h1>
        <p>Não há ficha com este endereço na base. O endereço pode estar digitado errado, ou o deputado ainda não foi carregado.</p>
        <div className="acoes">
          <Link className="btn" href="/">
            Voltar à busca
          </Link>
          <Link className="btn btn-sec" href="/deputados">
            Ver a lista de deputados
          </Link>
        </div>
      </div>
    </div>
  );
}
