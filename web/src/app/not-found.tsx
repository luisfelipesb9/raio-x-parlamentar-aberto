import Link from "next/link";

export default function NotFound() {
  return (
    <div className="pagina">
      <h1>Página não encontrada</h1>
      <p>O endereço pode ter mudado ou estar digitado errado.</p>
      <p>
        <Link className="btn" href="/">
          Voltar à busca
        </Link>
      </p>
    </div>
  );
}
