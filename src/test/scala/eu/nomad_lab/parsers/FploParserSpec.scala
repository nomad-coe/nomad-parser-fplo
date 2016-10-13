package eu.nomad_lab.parsers

import org.specs2.mutable.Specification

/**
 * FPLO output Test files:
 *
 * parsers/fplo/test/examples/dhcp_gd/out
 * parsers/fplo/test/examples/hcp_ti/out
 *
 */

object FploParserSpec extends Specification {
  "FploParserTest" >> {
    "test1 (dhcp Gd) with json-events" >> {
      ParserRun.parse(FploParser, "parsers/fplo/test/examples/dhcp_gd/out", "json-events") must_== ParseResult.ParseSuccess
    }
    "test1 (dhcp Gd) with json" >> {
      ParserRun.parse(FploParser, "parsers/fplo/test/examples/dhcp_gd/out", "json") must_== ParseResult.ParseSuccess
    }
    "test2 (hcp Ti) with json-events" >> {
      ParserRun.parse(FploParser, "parsers/fplo/test/examples/hcp_ti/out", "json-events") must_== ParseResult.ParseSuccess
    }
    "test2 (hcp Ti) with json" >> {
      ParserRun.parse(FploParser, "parsers/fplo/test/examples/hcp_ti/out", "json") must_== ParseResult.ParseSuccess
    }
  }
}
