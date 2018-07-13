/*
 * Copyright 2016-2018 Henning Glawe, Fawzi Mohamed
 * 
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 * 
 *     http://www.apache.org/licenses/LICENSE-2.0
 * 
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */

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
