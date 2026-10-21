package eu.kanade.tachiyomi.extension.en.batoto

import eu.kanade.tachiyomi.network.GET
import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import eu.kanade.tachiyomi.source.model.SManga
import eu.kanade.tachiyomi.source.online.ParsedHttpSource
import okhttp3.Headers
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import org.json.JSONObject
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element
import java.text.SimpleDateFormat
import java.util.ArrayList
import java.util.Locale
import java.util.concurrent.TimeUnit

class BatoTo : ParsedHttpSource() {

    override val name = "Bato.to"

    override val baseUrl = "https://bato1.com"

    override val lang = "en"

    override val supportsLatest = true

    override val client: OkHttpClient = network.cloudflareClient.newBuilder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    override fun headersBuilder(): Headers.Builder = super.headersBuilder()
        .set("Referer", "$baseUrl/")

    // ============================== Popular ==============================

    override fun popularMangaRequest(page: Int): Request {
        val path = if (page == 1) "/filter?sort=views" else "/filter?sort=views&page=$page"
        return GET("$baseUrl$path", headers)
    }

    override fun popularMangaSelector(): String = ".original.card-lg .unit, .unit"

    override fun popularMangaFromElement(element: Element): SManga = SManga.create().apply {
        val poster = element.selectFirst("a.poster, a[href*='/manga/']")
        val titleEl = element.selectFirst(".info > a, h3 a, a.item-title") ?: poster
        setUrlWithoutDomain(poster?.absUrl("href") ?: "")
        title = titleEl?.text().orEmpty()
        thumbnail_url = element.selectFirst("img")?.let {
            val data = it.attr("abs:data-src").ifEmpty { it.attr("abs:data-fallback") }
            if (data.isNotBlank()) data else it.attr("abs:src")
        }
    }

    override fun popularMangaNextPageSelector(): String = ".pagination a[rel=next], a:contains(Next)"

    // ============================== Latest ===============================

    override fun latestUpdatesRequest(page: Int): Request {
        val path = if (page == 1) "/updated" else "/updated/page/$page"
        return GET("$baseUrl$path", headers)
    }

    override fun latestUpdatesSelector(): String = popularMangaSelector()

    override fun latestUpdatesFromElement(element: Element): SManga = popularMangaFromElement(element)

    override fun latestUpdatesNextPageSelector(): String = popularMangaNextPageSelector()

    // ============================== Search ===============================

    override fun searchMangaRequest(page: Int, query: String, filters: FilterList): Request {
        val url = "$baseUrl/filter".toHttpUrl().newBuilder().apply {
            if (query.isNotBlank()) {
                addQueryParameter("keyword", query)
            }
            if (page > 1) {
                addQueryParameter("page", page.toString())
            }
            addQueryParameter("sort", "views")
        }.build()
        return GET(url.toString(), headers)
    }

    override fun searchMangaSelector(): String = popularMangaSelector()

    override fun searchMangaFromElement(element: Element): SManga = popularMangaFromElement(element)

    override fun searchMangaNextPageSelector(): String = popularMangaNextPageSelector()

    // ============================== Details ==============================

    override fun mangaDetailsParse(document: Document): SManga = SManga.create().apply {
        title = document.selectFirst("h1[itemprop=name], h1.item-title, h1")?.text().orEmpty()
        author = document.select(".meta div:has(span:contains(Author)) a, .item-author a").joinToString { it.text() }
        description = document.selectFirst(".description, .limit-html")?.text()
        genre = document.select(".meta div:has(span:contains(Genres)) a, .item-genres a").joinToString { it.text() }
        status = parseStatus(document.selectFirst(".info > p, .item-status")?.text())
        thumbnail_url = document.selectFirst(".poster img, img.item-poster")?.let {
            val data = it.attr("abs:data-src").ifEmpty { it.attr("abs:data-fallback") }
            if (data.isNotBlank()) data else it.attr("abs:src")
        }
    }

    private fun parseStatus(status: String?): Int = when (status?.lowercase(Locale.ENGLISH)?.trim()) {
        "ongoing", "releasing" -> SManga.ONGOING
        "completed" -> SManga.COMPLETED
        else -> SManga.UNKNOWN
    }

    // ============================== Chapters ==============================

    override fun chapterListRequest(manga: SManga): Request {
        val slug = manga.url.removeSuffix("/").substringAfterLast("/")
        return GET("$baseUrl/get-chapter-list?slug=$slug", headersBuilder().add("X-Requested-With", "XMLHttpRequest").build())
    }

    override fun chapterListParse(response: Response): List<SChapter> {
        val json = response.body.string()
        val jsonObject = JSONObject(json)
        val data = jsonObject.optJSONArray("data") ?: return emptyList()
        val slug = response.request.url.queryParameter("slug") ?: ""
        val list = ArrayList<SChapter>(data.length())
        val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ENGLISH)

        for (i in 0 until data.length()) {
            val item = data.getJSONObject(i)
            val chSlug = item.optString("chapter_slug")
            val chName = item.optString("chapter_name")
            val updated = item.optString("updated_at")
            val chapter = SChapter.create().apply {
                url = "/read/$slug/$chSlug"
                name = chName
                date_upload = try {
                    dateFormat.parse(updated)?.time ?: 0L
                } catch (e: Exception) {
                    0L
                }
            }
            list.add(chapter)
        }
        return list
    }

    override fun chapterFromElement(element: Element): SChapter = throw UnsupportedOperationException("Not used")

    // =============================== Pages ===============================

    override fun pageListParse(document: Document): List<Page> {
        val elements = document.select(".pages .page:not(.notice-page) img, .reader-pages img")
        val pages = ArrayList<Page>()
        for (i in 0 until elements.size) {
            val img = elements[i]
            val data = img.attr("abs:data-src").ifEmpty { img.attr("abs:data-fallback") }.ifEmpty { img.attr("abs:src") }
            if (data.isNotBlank() && !data.endsWith(".gif") && !data.contains("notice")) {
                pages.add(Page(pages.size, document.location(), data))
            }
        }
        return pages
    }

    override fun imageUrlParse(document: Document): String = throw UnsupportedOperationException("Not used")

    override fun imageRequest(page: Page): Request {
        return GET(page.imageUrl!!, headersBuilder().set("Referer", "$baseUrl/").build())
    }
}
