import { rotaDeTexto } from "@/content/rotas-next";

const rota = rotaDeTexto("faq");

export const generateMetadata = rota.generateMetadata;
export default rota.Pagina;
