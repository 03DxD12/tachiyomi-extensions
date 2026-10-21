package eu.kanade.tachiyomi.extension.en.manganelo

import eu.kanade.tachiyomi.multisrc.mangabox.MangaBox
import eu.kanade.tachiyomi.network.GET
import okhttp3.Headers
import okhttp3.Request
import java.text.SimpleDateFormat
import java.util.Locale

class Manganato : MangaBox("MangaNato", "https://natomanga.com", "en", SimpleDateFormat("MMM dd,yy", Locale.ENGLISH)) {
    override val id: Long = 1024627298672457456

    override fun headersBuilder(): Headers.Builder = super.headersBuilder().set("Referer", "https://natomanga.com")
    override fun popularMangaRequest(page: Int): Request = GET("$baseUrl/genre-all/$page?type=topview", headers)
    override fun popularMangaSelector() = "div.content-genres-item"
    override val latestUrlPath = "genre-all/"
    override val simpleQueryPath = "search/story/"
    override fun searchMangaSelector() = "div.search-story-item, div.content-genres-item"
}
