package eu.kanade.tachiyomi.extension.en.mangapill

import eu.kanade.tachiyomi.network.GET
import eu.kanade.tachiyomi.source.model.Filter
import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.MangasPage
import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import eu.kanade.tachiyomi.source.model.SManga
import eu.kanade.tachiyomi.source.online.ParsedHttpSource
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element
import java.util.Locale
import java.util.concurrent.TimeUnit

class MangaPill : ParsedHttpSource() {

    override val name = "MangaPill"

    override val baseUrl = "https://mangapill.com"

    override val lang = "en"

    override val supportsLatest = true

    override val client: OkHttpClient = network.cloudflareClient.newBuilder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    // Popular
    override fun popularMangaRequest(page: Int): Request = GET("$baseUrl/", headers)

    override fun popularMangaSelector(): String = "div:has(h4:contains(Trending)) > .grid > div:not([class])"

    override fun popularMangaFromElement(element: Element): SManga = SManga.create().apply {
        thumbnail_url = element.selectFirst("img")?.attr("data-src")
        setUrlWithoutDomain(element.selectFirst("a[href^='/manga/']")!!.absUrl("href"))
        title = element.selectFirst("div.line-clamp-2")!!.text()
    }

    override fun popularMangaNextPageSelector(): String? = null

    // Latest
    override fun latestUpdatesRequest(page: Int): Request = GET("$baseUrl/chapters", headers)

    override fun latestUpdatesSelector(): String = ".grid > div:not([class])"

    override fun latestUpdatesFromElement(element: Element): SManga = popularMangaFromElement(element)

    override fun latestUpdatesNextPageSelector(): String? = null

    // Search
    override fun searchMangaRequest(page: Int, query: String, filters: FilterList): Request {
        val url = "$baseUrl/search".toHttpUrl().newBuilder()
            .addQueryParameter("page", page.toString())
            .addQueryParameter("q", query)

        filters.forEach { filter ->
            when (filter) {
                is Status -> url.addQueryParameter("status", filter.toUriPart())
                is Type -> url.addQueryParameter("type", filter.toUriPart())
                else -> {}
            }
        }
        return GET(url.build().toString(), headers)
    }

    override fun searchMangaSelector(): String = ".grid > div:not([class])"

    override fun searchMangaFromElement(element: Element): SManga = popularMangaFromElement(element)

    override fun searchMangaNextPageSelector(): String = "a.btn.btn-sm"

    // Details
    override fun mangaDetailsParse(document: Document): SManga = SManga.create().apply {
        val genres = mutableListOf<String>()
        document.select("a[href*=genre]").forEach { element ->
            genres.add(element.text())
        }
        genre = genres.joinToString(", ")
        status = parseStatus(document.select("div.container > div:first-child > div:last-child > div:nth-child(3) > div:nth-child(2) > div").text())
        description = document.select("div.container > div:first-child > div:last-child > div:nth-child(2) > p").text()
        thumbnail_url = document.select("div.container > div:first-child > div:first-child > img").first()?.attr("data-src")
    }

    private fun parseStatus(element: String): Int = when {
        element.lowercase(Locale.ENGLISH).contains("publishing") -> SManga.ONGOING
        element.lowercase(Locale.ENGLISH).contains("finished") -> SManga.COMPLETED
        else -> SManga.UNKNOWN
    }

    // Chapters
    override fun chapterListSelector(): String = "#chapters > div > a"

    override fun chapterFromElement(element: Element): SChapter = SChapter.create().apply {
        setUrlWithoutDomain(element.absUrl("href"))
        name = element.text()
        date_upload = 0L
    }

    // Pages
    override fun pageListParse(document: Document): List<Page> {
        return document.select("picture img").mapIndexed { i, it ->
            Page(i, imageUrl = it.attr("data-src"))
        }
    }

    override fun imageUrlParse(document: Document): String = throw UnsupportedOperationException("Not used")

    // Filters
    override fun getFilterList() = FilterList(
        Filter.Header("NOTE: Ignored if using text search!"),
        Filter.Separator(),
        Status(),
        Type(),
    )

    private open class UriPartFilter(
        displayName: String,
        private val vals: Array<Pair<String, String>>,
    ) : Filter.Select<String>(displayName, vals.map { it.first }.toTypedArray()) {
        fun toUriPart() = vals[state].second
    }

    private class Status : UriPartFilter(
        "Status",
        arrayOf(
            Pair("All", ""),
            Pair("Publishing", "publishing"),
            Pair("Finished", "finished"),
            Pair("On Hiatus", "on-hiatus"),
            Pair("Discontinued", "discontinued"),
        ),
    )

    private class Type : UriPartFilter(
        "Type",
        arrayOf(
            Pair("All", ""),
            Pair("Manga", "manga"),
            Pair("Novel", "novel"),
            Pair("One-Shot", "one-shot"),
            Pair("Doujinshi", "doujinshi"),
            Pair("Manhwa", "manhwa"),
            Pair("Manhua", "manhua"),
            Pair("OEL", "oel"),
        ),
    )
}
