import { rotaDeTexto } from "@/content/rotas-next";

const rota = rotaDeTexto("dados-e-api");

export const generateMetadata = rota.generateMetadata;
export default rota.Pagina;
