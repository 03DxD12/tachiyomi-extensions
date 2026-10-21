package eu.kanade.tachiyomi.extension.en.mangabat

import eu.kanade.tachiyomi.multisrc.mangabox.MangaBox
import okhttp3.Headers

class Mangabat : MangaBox("MangaBat", "https://www.mangabats.com", "en") {
    override fun headersBuilder(): Headers.Builder = super.headersBuilder().set("Referer", "https://readmangabat.com")
    override val simpleQueryPath = "search/manga/"
    override fun searchMangaSelector() = "${super.searchMangaSelector()}, div.list-truyen-item-wrap"
}
