APP_STYLE = """
QMainWindow {
    background-color: #1f2d35;
}

QWidget#RootWidget {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #1f2d35,
        stop:0.45 #2f4548,
        stop:1 #5d6f63
    );
}

QWidget#Card {
    background-color: rgba(239, 235, 222, 225);
    border: 2px solid rgba(214, 205, 184, 190);
    border-radius: 18px;
}

QWidget#SoftBlueCard {
    background-color: rgba(213, 229, 229, 220);
    border: 2px solid rgba(180, 203, 202, 190);
    border-radius: 18px;
}

QWidget#DarkCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #24394a,
        stop:1 #4d6d76
    );
    border: 2px solid rgba(178, 200, 196, 170);
    border-radius: 18px;
}

QWidget#DateCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #f4c47a,
        stop:0.48 #e7d3a6,
        stop:1 #d6e1d3
    );
    border: 2px solid rgba(235, 214, 166, 210);
    border-radius: 20px;
}

QWidget#StocksCard {
    background-color: rgba(37, 54, 63, 230);
    border: 2px solid rgba(144, 169, 166, 170);
    border-radius: 18px;
}

QWidget#WeatherRow {
    background-color: rgba(239, 235, 222, 215);
    border: 2px solid rgba(214, 205, 184, 170);
    border-radius: 15px;
}

QWidget#WeatherRowNow {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #f4c47a,
        stop:1 #e9d7b6
    );
    border: 2px solid #e8c477;
    border-radius: 15px;
}

QWidget#ImagePlaceholderLight {
    background-color: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #cadbdf,
        stop:0.55 #e2e1cf,
        stop:1 #e4c8a9
    );
    border: 2px solid rgba(173, 196, 192, 190);
    border-radius: 14px;
}

QWidget#ImagePlaceholderDark {
    background-color: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #253f55,
        stop:0.6 #416a78,
        stop:1 #879b82
    );
    border: 2px solid rgba(169, 190, 192, 170);
    border-radius: 14px;
}

QWidget#StockRow {
    background-color: rgba(255, 248, 230, 35);
    border: 1px solid rgba(197, 213, 207, 70);
    border-radius: 12px;
}

QWidget#IndexMiniCard {
    background-color: rgba(255, 248, 230, 42);
    border: 1px solid rgba(197, 213, 207, 80);
    border-radius: 12px;
}

QWidget#StockGainPill {
    background-color: rgba(98, 151, 108, 80);
    border: 1px solid rgba(148, 201, 157, 120);
    border-radius: 8px;
}

QWidget#StockLossPill {
    background-color: rgba(170, 93, 93, 80);
    border: 1px solid rgba(210, 145, 145, 120);
    border-radius: 8px;
}

QWidget#TodayReminderRow {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #efd9a0,
        stop:1 #efe8d8
    );
    border: 1px solid #d3b86b;
    border-radius: 12px;
}

QWidget#NewspaperSportsCard {
    background-color: rgba(247, 241, 229, 240);
    border: 2px solid rgba(166, 149, 122, 170);
    border-radius: 14px;
}

QWidget#PaperFeaturedStory {
    background-color: rgba(255, 250, 241, 150);
    border: 1px solid rgba(155, 137, 112, 110);
    border-radius: 8px;
}

QWidget#PaperStory {
    background-color: rgba(255, 252, 247, 110);
    border: 1px solid rgba(155, 137, 112, 95);
    border-radius: 8px;
}

QWidget#ScoreboardCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #17262d,
        stop:0.48 #263c3f,
        stop:1 #3f5146
    );
    border: 2px solid rgba(160, 190, 185, 150);
    border-radius: 16px;
}

QWidget#LeagueScoreboard {
    background-color: rgba(8, 18, 22, 95);
    border: 1px solid rgba(170, 205, 195, 100);
    border-radius: 12px;
}

QWidget#ScoreboardGameTile {
    background-color: rgba(245, 235, 196, 28);
    border: 1px solid rgba(245, 235, 196, 70);
    border-radius: 9px;
}

QWidget#NewspaperGamesCard {
    background-color: rgba(247, 241, 229, 235);
    border: 2px solid rgba(166, 149, 122, 170);
    border-radius: 14px;
}

QWidget#PaperLeagueColumn {
    background-color: rgba(255, 252, 247, 95);
    border: 1px solid rgba(155, 137, 112, 95);
    border-radius: 8px;
}

QWidget#PaperGameListing {
    background-color: rgba(255, 250, 241, 120);
    border: 1px solid rgba(155, 137, 112, 80);
    border-radius: 7px;
}

QLabel#PaperGamesMasthead {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 24px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 1px;
}

QLabel#PaperGamesEdition {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 9px;
    font-weight: 700;
    color: #6b5f50;
    letter-spacing: 1px;
}

QLabel#PaperScheduleTag {
    font-family: "Arial";
    font-size: 9px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #7a5f43;
    border-radius: 8px;
    padding: 3px;
}

QLabel#PaperLeagueTitle {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 20px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 1px;
}

QLabel#PaperGameTime {
    font-family: "Arial";
    font-size: 9px;
    font-weight: 900;
    color: #9a4d3d;
    letter-spacing: 1px;
}

QLabel#PaperGameMatchup {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 14px;
    font-weight: 900;
    color: #2b2621;
}

QLabel#PaperGameDetail {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 10px;
    font-weight: 500;
    color: #5b5045;
}
QWidget#CleanGamesCard {
    background-color: rgba(247, 241, 229, 235);
    border: 2px solid rgba(166, 149, 122, 170);
    border-radius: 14px;
}

QWidget#CleanGameCard {
    background-color: rgba(255, 250, 241, 125);
    border: 1px solid rgba(155, 137, 112, 90);
    border-radius: 8px;
}

QLabel#CleanGamesTitle {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 22px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 1px;
}

QLabel#CleanGamesSubtitle {
    font-family: "Arial";
    font-size: 9px;
    font-weight: 900;
    color: #7a5f43;
    letter-spacing: 1px;
}

QLabel#CleanLeagueTitle {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 22px;
    font-weight: 900;
    color: #2f2a24;
}

QLabel#CleanGameTime {
    font-family: "Arial";
    font-size: 10px;
    font-weight: 900;
    color: #9a4d3d;
}

QLabel#CleanGameMatchup {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 15px;
    font-weight: 900;
    color: #2b2621;
}

QLabel#CleanGameDetail {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 10px;
    font-weight: 600;
    color: #5b5045;
}

QWidget#GameDayCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #efe6d2,
        stop:1 #d9c8a8
    );
    border: 2px solid rgba(126, 103, 76, 170);
    border-radius: 14px;
}

QWidget#GameDayLeagueCard {
    background-color: rgba(255, 250, 239, 135);
    border: 1px solid rgba(116, 95, 70, 120);
    border-radius: 10px;
}

QWidget#GameDayMatchupBox {
    background-color: rgba(45, 58, 62, 210);
    border: 1px solid rgba(230, 210, 160, 130);
    border-radius: 8px;
}

QLabel#GameDayTitle {
    font-size: 24px;
    font-weight: 900;
    color: #2d2a24;
    letter-spacing: 1px;
}

QLabel#GameDaySubtitle {
    font-size: 10px;
    font-weight: 900;
    color: #735d3f;
    letter-spacing: 1px;
}

QLabel#GameDayLeague {
    font-size: 22px;
    font-weight: 900;
    color: #2d2a24;
}

QLabel#GameDayTime {
    font-size: 10px;
    font-weight: 900;
    color: #e9c46a;
}

QLabel#GameDayMatchup {
    font-size: 13px;
    font-weight: 900;
    color: #fff8e8;
}

QLabel#GameDayDetail {
    font-size: 9px;
    font-weight: 700;
    color: #cfd8d3;
}
QWidget#MarketTapeCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #17262d,
        stop:0.50 #22383b,
        stop:1 #3c4939
    );
    border: 2px solid rgba(205, 184, 125, 145);
    border-radius: 15px;
}

QWidget#MarketTapeIndexCard {
    background-color: rgba(245, 232, 181, 32);
    border: 1px solid rgba(231, 205, 132, 95);
    border-radius: 9px;
}

QWidget#MarketTapeStockTile {
    background-color: rgba(7, 17, 21, 115);
    border: 1px solid rgba(180, 205, 190, 80);
    border-radius: 10px;
}

QLabel#MarketTapeTitle {
    font-size: 18px;
    font-weight: 900;
    color: #f2e5b8;
    letter-spacing: 1px;
}

QLabel#MarketTapeSubtitle {
    font-size: 8px;
    font-weight: 800;
    color: #b7c7bd;
    letter-spacing: 1px;
}

QLabel#MarketTapeBadge {
    font-size: 9px;
    font-weight: 900;
    color: #1a272c;
    background-color: #e2c66f;
    border-radius: 9px;
    padding: 3px;
}

QLabel#MarketTapeSectionLabel {
    font-size: 8px;
    font-weight: 900;
    color: #d9c98f;
    letter-spacing: 1px;
}

QLabel#MarketTapeIndexName {
    font-size: 9px;
    font-weight: 900;
    color: #d9c98f;
    letter-spacing: 1px;
}

QLabel#MarketTapeIndexPrice {
    font-size: 16px;
    font-weight: 900;
    color: #f7f1dc;
}

QLabel#MarketTapePrice {
    font-size: 15px;
    font-weight: 900;
    color: #f7f1dc;
}

QWidget#MarketTapeAHBox {
    background-color: rgba(255, 255, 255, 18);
    border: 1px solid rgba(255, 255, 255, 38);
    border-radius: 8px;
}

QLabel#MarketTapeAHLabel {
    font-size: 7px;
    font-weight: 900;
    color: #c6d3cc;
    letter-spacing: 1px;
}

QWidget#RemindersCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #f1ead9,
        stop:1 #d8c9ac
    );
    border: 2px solid rgba(126, 103, 76, 150);
    border-radius: 14px;
}

QLabel#RemindersTitle {
    font-size: 18px;
    font-weight: 900;
    color: #2d2a24;
    letter-spacing: 1px;
}

QLabel#ReminderTodayBadge {
    font-size: 9px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #8e5f45;
    border-radius: 9px;
    padding: 3px;
}

QLabel#TodayReminderGroupTitle {
    font-size: 9px;
    font-weight: 900;
    color: #8e5f45;
    letter-spacing: 1px;
}

QLabel#UpcomingReminderGroupTitle {
    font-size: 8px;
    font-weight: 900;
    color: rgba(74, 62, 48, 155);
    letter-spacing: 1px;
}

QWidget#TodayReminderRow {
    background-color: rgba(255, 248, 234, 190);
    border: 2px solid rgba(142, 95, 69, 125);
    border-radius: 11px;
}

QWidget#UpcomingReminderRow {
    background-color: rgba(255, 250, 240, 80);
    border: 1px solid rgba(116, 95, 70, 70);
    border-radius: 8px;
}

QLabel#TodayReminderIcon {
    font-size: 20px;
}

QLabel#UpcomingReminderIcon {
    font-size: 13px;
    color: rgba(74, 62, 48, 150);
}

QLabel#TodayReminderText {
    font-size: 16px;
    font-weight: 900;
    color: #2d2a24;
}

QLabel#UpcomingReminderText {
    font-size: 10px;
    font-weight: 700;
    color: rgba(47, 42, 36, 165);
}

QWidget#FoxNewsCard {
    background-color: rgba(239, 232, 217, 245);
    border: 2px solid rgba(173, 147, 118, 150);
    border-radius: 18px;
}

QWidget#CnbcNewsCard {
    background-color: rgba(225, 234, 229, 245);
    border: 2px solid rgba(116, 152, 151, 150);
    border-radius: 18px;
}

QWidget#FoxNewsTextPanel {
    background-color: rgba(247, 241, 229, 245);
    border-bottom-left-radius: 18px;
    border-bottom-right-radius: 18px;
}

QWidget#CnbcNewsTextPanel {
    background-color: rgba(232, 238, 232, 245);
    border-bottom-left-radius: 18px;
    border-bottom-right-radius: 18px;
}

QLabel#FoxSourcePill {
    font-size: 10px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #b56a58;
    border-radius: 8px;
    padding: 4px 10px;
}

QLabel#CnbcSourcePill {
    font-size: 10px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #4f89a0;
    border-radius: 8px;
    padding: 4px 10px;
}

QLabel#FoxNewsKicker {
    font-size: 8px;
    font-weight: 900;
    color: #8a5e4b;
    letter-spacing: 1px;
}

QLabel#CnbcNewsKicker {
    font-size: 8px;
    font-weight: 900;
    color: #54747d;
    letter-spacing: 1px;
}

QLabel#FoxHeadlineText {
    font-size: 21px;
    font-weight: 900;
    color: #24323b;
    line-height: 1.1em;
}

QLabel#CnbcHeadlineText {
    font-size: 21px;
    font-weight: 900;
    color: #24323b;
    line-height: 1.1em;
}




QLabel#NewsPaperMasthead {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 27px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 2px;
}

QLabel#NewsPaperEdition {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 9px;
    font-weight: 700;
    color: #6b5f50;
    letter-spacing: 1px;
}

QLabel#NewsPaperKicker {
    font-family: "Arial";
    font-size: 8px;
    font-weight: 900;
    color: #9a4d3d;
    letter-spacing: 1px;
}

QLabel#NewsPaperHeadline {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 23px;
    font-weight: 900;
    color: #2b2621;
}

QLabel#NewsPaperFooter {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 8px;
    font-weight: 700;
    color: #7a6d5c;
}

QLabel#MarketTapeUp {
    font-size: 11px;
    font-weight: 900;
    color: #eaf6df;
    background-color: rgba(86, 133, 91, 130);
    border-radius: 6px;
    padding: 1px;
}

QLabel#MarketTapeDown {
    font-size: 11px;
    font-weight: 900;
    color: #fff0ea;
    background-color: rgba(139, 75, 68, 130);
    border-radius: 6px;
    padding: 1px;
}

QLabel#MarketTapeTicker {
    font-size: 13px;
    font-weight: 900;
    color: #f7f1dc;
    letter-spacing: 1px;
}

QLabel#ScoreboardMainTitle {
    font-size: 14px;
    font-weight: 900;
    color: #e8f1dd;
    letter-spacing: 1px;
}

QLabel#ScoreboardStatusBadge {
    font-size: 10px;
    font-weight: 900;
    color: #17262d;
    background-color: #e5d08d;
    border-radius: 9px;
    padding: 3px;
}

QLabel#ScoreboardLeagueTitle {
    font-size: 22px;
    font-weight: 900;
    color: #f4e7ad;
    letter-spacing: 1px;
}

QLabel#ScoreboardLight {
    font-size: 10px;
    font-weight: 900;
    color: #f1c76a;
}

QLabel#ScoreboardMatchup {
    font-size: 12px;
    font-weight: 900;
    color: #f1f6ec;
}

QLabel#ScoreboardTimeBadge {
    font-size: 10px;
    font-weight: 900;
    color: #17262d;
    background-color: #b6d4c8;
    border-radius: 7px;
    padding: 2px;
}

QLabel#ScoreboardDetail {
    font-size: 9px;
    font-weight: 700;
    color: #c7d7cd;
}

QLabel#PaperMasthead {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 30px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 2px;
}

QLabel#PaperEditionLine {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 10px;
    font-weight: 700;
    color: #6b5f50;
    letter-spacing: 1px;
}

QLabel#PaperKicker {
    font-family: "Arial";
    font-size: 9px;
    font-weight: 900;
    color: #7a5f43;
    letter-spacing: 1px;
}

QLabel#PaperKickerFeatured {
    font-family: "Arial";
    font-size: 9px;
    font-weight: 900;
    color: #9a4d3d;
    letter-spacing: 1px;
}

QLabel#PaperHeadlineFeatured {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 17px;
    font-weight: 900;
    color: #2b2621;
    line-height: 1.1em;
}

QWidget#NewspaperNewsCard {
    background-color: rgba(247, 241, 229, 240);
    border: 2px solid rgba(166, 149, 122, 170);
    border-radius: 15px;
}

QWidget#NewsPaperPhotoBox {
    background-color: rgba(255, 250, 241, 150);
    border: 1px solid rgba(117, 97, 72, 130);
    border-radius: 10px;
}

QWidget#NewsPaperStoryPanel {
    background-color: rgba(255, 252, 247, 125);
    border: 1px solid rgba(155, 137, 112, 95);
    border-radius: 10px;
}

QLabel#OldNewsSourceName {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 25px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 2px;
}

QLabel#OldNewsEditionSmall {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 8px;
    font-weight: 900;
    color: #7a6d5c;
    letter-spacing: 1px;
}

QLabel#OldNewsHeadline {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 22px;
    font-weight: 900;
    color: #2b2621;
}

QLabel#OldNewsFooter {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 8px;
    font-weight: 800;
    color: #8b4e3f;
    letter-spacing: 1px;
}

QLabel#OldNewsPageNumber {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 900;
    color: #6b5f50;
    letter-spacing: 1px;
}

QLabel#OldNewsTopMasthead {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 27px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 2px;
}

QLabel#OldNewsKicker {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 10px;
    font-weight: 900;
    color: #8b4e3f;
    letter-spacing: 2px;
}

QWidget#NewspaperSportsCard {
    background-color: rgba(247, 241, 229, 240);
    border: 2px solid rgba(166, 149, 122, 170);
    border-radius: 14px;
}

QWidget#PaperFeaturedStory {
    background-color: rgba(255, 250, 241, 150);
    border: 1px solid rgba(155, 137, 112, 110);
    border-radius: 8px;
}

QWidget#PaperStory {
    background-color: rgba(255, 252, 247, 110);
    border: 1px solid rgba(155, 137, 112, 95);
    border-radius: 8px;
}

QWidget#PaperLeagueColumn {
    background-color: rgba(255, 252, 247, 110);
    border: 1px solid rgba(155, 137, 112, 95);
    border-radius: 8px;
}

QWidget#PaperGameListing {
    background-color: rgba(255, 250, 241, 120);
    border: 1px solid rgba(155, 137, 112, 75);
    border-radius: 7px;
}

QLabel#PaperMasthead {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 25px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 2px;
}

QLabel#PaperEditionLine {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 9px;
    font-weight: 700;
    color: #6b5f50;
    letter-spacing: 1px;
}

QLabel#PaperKicker {
    font-family: "Arial";
    font-size: 8px;
    font-weight: 900;
    color: #7a5f43;
    letter-spacing: 1px;
}

QLabel#PaperKickerFeatured {
    font-family: "Arial";
    font-size: 8px;
    font-weight: 900;
    color: #9a4d3d;
    letter-spacing: 1px;
}

QLabel#PaperHeadlineFeatured {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 13px;
    font-weight: 900;
    color: #2b2621;
}

QLabel#PaperHeadline {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 10px;
    font-weight: 800;
    color: #2f2a24;
}

QLabel#PaperLeagueTitle {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 18px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 1px;
}

QLabel#PaperGameTime {
    font-family: "Arial";
    font-size: 8px;
    font-weight: 900;
    color: #9a4d3d;
    letter-spacing: 1px;
}

QLabel#PaperGameMatchup {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 11px;
    font-weight: 900;
    color: #2b2621;
}

QLabel#PaperGameDetail {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 8px;
    font-weight: 600;
    color: #5b5045;
}

QLabel#PaperFooterLeft {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 8px;
    font-weight: 800;
    color: #7a6d5c;
    letter-spacing: 1px;
}

QLabel#PaperFooterPage {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 900;
    color: #6b5f50;
    letter-spacing: 1px;
}

QLabel#PaperLeagueEmoji {
    font-size: 16px;
}

QWidget#PaperGameListing {
    background-color: rgba(255, 250, 241, 125);
    border: 1px solid rgba(155, 137, 112, 75);
    border-radius: 7px;
}

QWidget#PaperGameListingEmpty {
    background-color: rgba(255, 250, 241, 55);
    border: 1px dashed rgba(155, 137, 112, 70);
    border-radius: 7px;
}

QLabel#PaperGameTime {
    font-family: "Arial";
    font-size: 8px;
    font-weight: 900;
    color: #9a4d3d;
    letter-spacing: 1px;
}

QLabel#PaperGameTimeEmpty {
    font-family: "Arial";
    font-size: 8px;
    font-weight: 900;
    color: rgba(90, 78, 63, 115);
    letter-spacing: 1px;
}

QLabel#PaperGameMatchupEmpty {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 9px;
    font-weight: 700;
    color: rgba(47, 42, 36, 125);
}

QLabel#PaperGameDetailEmpty {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 7px;
    font-weight: 600;
    color: rgba(91, 80, 69, 105);
}

QLabel#OldNewsReadLink {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 8px;
    font-weight: 900;
    color: #8b4e3f;
    letter-spacing: 1px;
}

QLabel#DateWeatherTemp {
    font-size: 18px;
    font-weight: 900;
    color: #f8ead2;
    letter-spacing: 1px;
}

QLabel#DateWeatherHour {
    font-size: 10px;
    font-weight: 900;
    color: rgba(248, 234, 210, 190);
    letter-spacing: 1px;
}

QWidget#DateCardWeatherOverlay {
    background-color: transparent;
    border: none;
}

QWidget#DateWeatherBackground {
    border-radius: 14px;
}

QLabel#DateDayWeather {
    font-size: 36px;
    font-weight: 900;
    letter-spacing: 1px;
}

QLabel#DateMonthWeather {
    font-size: 18px;
    font-weight: 900;
}

QLabel#DateNumberWeather {
    font-size: 58px;
    font-weight: 900;
}

QLabel#DateCurrentWeather {
    font-size: 24px;
    font-weight: 900;
    letter-spacing: 1px;
}

QLabel#DateSubtitleWeather {
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 1px;
}

QLabel#PaperHeadline {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 11px;
    font-weight: 700;
    color: #2f2a24;
    line-height: 1.1em;
}

QLabel#PaperNote {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 10px;
    font-weight: 500;
    color: #40372e;
    line-height: 1.1em;
}

QWidget#UpcomingReminderRow {
    background-color: rgba(255, 248, 230, 80);
    border: 1px solid rgba(214, 205, 184, 140);
    border-radius: 10px;
}

QWidget#TodayReminderRow {
    background-color: rgba(239, 217, 160, 150);
    border: 1px solid rgba(211, 184, 107, 170);
    border-radius: 9px;
}

QWidget#UpcomingReminderRow {
    background-color: rgba(255, 248, 230, 70);
    border: 1px solid rgba(214, 205, 184, 110);
    border-radius: 9px;
}

QWidget#SportsCreativeCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(214, 229, 229, 230),
        stop:0.48 rgba(239, 235, 222, 225),
        stop:1 rgba(225, 210, 183, 220)
    );
    border: 2px solid rgba(180, 203, 202, 190);
    border-radius: 18px;
}

QLabel#SportsCreativeTitle {
    font-size: 28px;
    font-weight: 900;
    color: #25313b;
}

QLabel#SportsCreativeSubtitle {
    font-size: 11px;
    font-weight: 900;
    color: #6f807a;
    letter-spacing: 1px;
}

QLabel#SportsLiveBadge {
    font-size: 11px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #b76e5f;
    border: 1px solid rgba(255, 248, 236, 120);
    border-radius: 12px;
    padding: 3px;
}

QWidget#FeaturedSportsStory {
    background-color: rgba(255, 248, 230, 145);
    border: 1px solid rgba(183, 110, 95, 130);
    border-radius: 12px;
}

QWidget#SportsStoryRow {
    background-color: rgba(255, 248, 230, 85);
    border: 1px solid rgba(214, 205, 184, 110);
    border-radius: 10px;
}

QLabel#SportsNumberBadge {
    font-size: 12px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #6f807a;
    border-radius: 9px;
}

QLabel#FeaturedSportsNumberBadge {
    font-size: 13px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #b76e5f;
    border-radius: 9px;
}

QLabel#SportsHeadline {
    font-size: 14px;
    font-weight: 700;
    color: #35434d;
}

QLabel#TodayReminderText {
    font-size: 17px;
    font-weight: 900;
    color: #25313b;
}

QLabel#UpcomingReminderText {
    font-size: 13px;
    font-weight: 700;
    color: #3b4a52;
}

QLabel#ReminderGroupTitle {
    font-size: 13px;
    font-weight: 900;
    color: #6f807a;
    letter-spacing: 1px;
}

QLabel#SectionTitle {
    font-size: 28px;
    font-weight: 900;
    color: #25313b;
}

QLabel#StockTicker {
    font-size: 13px;
    font-weight: 900;
    color: #a9bbb4;
}

QLabel#StockPrice {
    font-size: 20px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#StockUp {
    font-size: 11px;
    font-weight: 900;
    color: #a8d5a2;
}

QLabel#StockDown {
    font-size: 11px;
    font-weight: 900;
    color: #e0a2a2;
}

QLabel#IndexPrice {
    font-size: 17px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#IndexName {
    font-size: 11px;
    font-weight: 900;
    color: #a9bbb4;
}

QLabel {
    font-family: Arial;
    color: #263238;
}

QLabel#DateDay {
    font-size: 56px;
    font-weight: 900;
    color: #25313b;
}

QLabel#DateMonth {
    font-size: 24px;
    font-weight: 900;
    color: #4a5b58;
}

QLabel#DateNumber {
    font-size: 72px;
    font-weight: 900;
    color: #25313b;
}

QLabel#DateSubtitle {
    font-size: 12px;
    font-weight: 900;
    color: #6f7463;
    letter-spacing: 1px;
}

QLabel#MorningArt {
    font-size: 30px;
    font-weight: 900;
    color: #b96e3f;
}

QLabel#WeatherText {
    font-size: 25px;
    font-weight: 800;
    color: #263238;
}

QLabel#SectionTitle {
    font-size: 37px;
    font-weight: 900;
    color: #25313b;
}

QLabel#SectionSubtitle {
    font-size: 13px;
    font-weight: 800;
    color: #7b8b87;
    letter-spacing: 1px;
}

QLabel#SmallSectionTitle {
    font-size: 15px;
    font-weight: 900;
    color: #dbe8df;
    letter-spacing: 1px;
}

QLabel#StocksHeaderRight {
    font-size: 12px;
    font-weight: 900;
    color: #a9bbb4;
    letter-spacing: 1px;
}

QLabel#SportsHeadline {
    font-size: 16px;
    font-weight: 600;
    color: #35434d;
}

QLabel#FoxHeadline {
    font-size: 29px;
    font-weight: 900;
    color: #9f4f45;
}

QLabel#CnbcHeadline {
    font-size: 27px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#LeagueTitle {
    font-size: 28px;
    font-weight: 900;
    color: #25313b;
}

QLabel#GameText {
    font-size: 13px;
    font-weight: 800;
    color: #33424b;
}

QLabel#IndexName {
    font-size: 12px;
    font-weight: 900;
    color: #a9bbb4;
}

QLabel#IndexPrice {
    font-size: 19px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#StockTicker {
    font-size: 15px;
    font-weight: 900;
    color: #a9bbb4;
}

QLabel#StockPrice {
    font-size: 25px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#AfterHoursLabel {
    font-size: 9px;
    font-weight: 900;
    color: #a9bbb4;
}

QLabel#StockUp {
    font-size: 12px;
    font-weight: 900;
    color: #a8d5a2;
}

QLabel#StockDown {
    font-size: 12px;
    font-weight: 900;
    color: #e0a2a2;
}

QLabel#ReminderGroupTitle {
    font-size: 16px;
    font-weight: 900;
    color: #6f807a;
    letter-spacing: 1px;
}

QLabel#TodayReminderText {
    font-size: 22px;
    font-weight: 900;
    color: #25313b;
}

QLabel#UpcomingReminderText {
    font-size: 16px;
    font-weight: 700;
    color: #3b4a52;
}

QLabel#ImageBadge {
    font-size: 17px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #b76e5f;
    border-radius: 8px;
    padding: 5px 10px;
}

QLabel#ImageBadgeBlue {
    font-size: 17px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #4f7686;
    border-radius: 8px;
    padding: 5px 10px;
}

QLabel#ImageGraphicText {
    font-size: 24px;
    font-weight: 900;
    color: #536b6a;
}

QLabel#ImageGraphicTextDark {
    font-size: 24px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#SkyArt {
    font-size: 42px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#SkyArtLight {
    font-size: 42px;
    font-weight: 900;
    color: #7a938e;
}
"""